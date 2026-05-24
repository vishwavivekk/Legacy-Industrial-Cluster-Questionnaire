"""
Persistence layer with two backends:

  1. MongoDB (preferred) — when `mongodb_uri` is set in st.secrets or the
     MONGODB_URI env var is exported. Designed for MongoDB Atlas
     (mongodb+srv://...), works equally with any standard mongo URI.
  2. Google Sheets (fallback) — when Mongo isn't configured but
     `sheet_id` plus service-account credentials are present.

If neither is configured the app raises a clear error on first write,
rather than silently dropping data.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st


# ─── Backend detection ───────────────────────────────────────────────
_USE_MONGO = False
_USE_SHEETS = False


def _secret(name: str, default: Any = None) -> Any:
    """Safe read from st.secrets that falls back to env vars."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except (FileNotFoundError, RuntimeError, KeyError):
        pass
    return os.getenv(name.upper(), default)


# Try MongoDB first
try:
    _mongo_uri = _secret("mongodb_uri") or os.getenv("MONGODB_URI")
    if _mongo_uri:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
        _USE_MONGO = True
except Exception:
    _USE_MONGO = False

# Then Sheets
if not _USE_MONGO:
    try:
        if "sheet_id" in st.secrets and (
            st.secrets.get("gcp_service_account_json")
            or "gcp_service_account" in st.secrets
        ):
            import gspread
            from google.oauth2.service_account import Credentials
            _USE_SHEETS = True
    except Exception:
        _USE_SHEETS = False


_LOCK = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
# MONGODB BACKEND (preferred)
# ═══════════════════════════════════════════════════════════════════
if _USE_MONGO:
    DB_NAME = str(_secret("mongodb_db", "nicdc"))
    COLL_NAME = str(_secret("mongodb_collection", "responses"))
    COUNTER_COLL = "counters"  # for atomic auto-incrementing id

    @st.cache_resource(show_spinner=False)
    def _get_client() -> "MongoClient":
        uri = _secret("mongodb_uri") or os.getenv("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=10000, appname="nicdc-questionnaire")
        # Force a round-trip so we fail fast on bad credentials
        client.admin.command("ping")
        return client

    def _coll():
        return _get_client()[DB_NAME][COLL_NAME]

    def _counters():
        return _get_client()[DB_NAME][COUNTER_COLL]

    def _next_id() -> int:
        """Atomic auto-increment using findOneAndUpdate."""
        doc = _counters().find_one_and_update(
            {"_id": "responses"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,  # ReturnDocument.AFTER — but pymongo accepts bool
        )
        # Some pymongo versions need explicit enum; fall back if needed
        if doc is None or "seq" not in doc:
            from pymongo import ReturnDocument
            doc = _counters().find_one_and_update(
                {"_id": "responses"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        return int(doc["seq"])

    def init_db() -> None:
        with _LOCK:
            coll = _coll()
            try:
                coll.create_index("id", unique=True)
                coll.create_index("submitted_at")
                coll.create_index("cluster_name")
            except PyMongoError:
                pass

    def save_response(payload: dict) -> int:
        init_db()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
        with _LOCK:
            new_id = _next_id()
            doc = {
                "id": new_id,
                "submitted_at": now,
                "cluster_name": str(payload.get("general__cluster_name", "")),
                "cluster_product": str(payload.get("general__cluster_product", "")),
                "cluster_geo": str(payload.get("general__cluster_geo", "")),
                "respondent": str(payload.get("general__respondent", "")),
                "respondent_contact": str(payload.get("general__respondent_contact", "")),
                "payload": payload,
            }
            _coll().insert_one(doc)
            return int(new_id)

    def _summary_cols() -> list[str]:
        return ["id", "submitted_at", "cluster_name", "cluster_product",
                "cluster_geo", "respondent", "respondent_contact"]

    def list_responses() -> pd.DataFrame:
        init_db()
        with _LOCK:
            cursor = _coll().find(
                {},
                projection={"_id": 0, "payload": 0},
            ).sort("id", -1)
            rows = list(cursor)
        cols = _summary_cols()
        if not rows:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(rows)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols]

    def get_response(response_id: int):
        with _LOCK:
            doc = _coll().find_one({"id": int(response_id)}, projection={"_id": 0})
        if doc is None:
            return None
        # Ensure shape matches the rest of the app (payload key present)
        if "payload" not in doc:
            doc["payload"] = {}
        return doc

    def delete_response(response_id: int) -> None:
        with _LOCK:
            _coll().delete_one({"id": int(response_id)})

    def export_dataframe() -> pd.DataFrame:
        init_db()
        with _LOCK:
            cursor = _coll().find({}, projection={"_id": 0}).sort("id", 1)
            docs = list(cursor)
        if not docs:
            return pd.DataFrame()
        rows = []
        for d in docs:
            payload = d.get("payload", {}) or {}
            flat: dict = {}
            for k, v in payload.items():
                if isinstance(v, list):
                    flat[k] = " | ".join(str(x) for x in v)
                elif isinstance(v, dict):
                    flat[k] = json.dumps(v, ensure_ascii=False)
                else:
                    flat[k] = v
            flat["id"] = d.get("id")
            flat["submitted_at"] = d.get("submitted_at")
            rows.append(flat)
        df = pd.DataFrame(rows)
        front = ["id", "submitted_at"]
        cols = front + [c for c in df.columns if c not in front]
        return df[cols]


# ═══════════════════════════════════════════════════════════════════
# GOOGLE SHEETS BACKEND (fallback)
# ═══════════════════════════════════════════════════════════════════
elif _USE_SHEETS:
    HEADERS = [
        "id", "submitted_at",
        "cluster_name", "cluster_product", "cluster_geo",
        "respondent", "respondent_contact",
        "payload_json",
    ]
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    def _normalise_private_key(pk: str) -> str:
        if not isinstance(pk, str) or "BEGIN PRIVATE KEY" not in pk:
            return pk
        if "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        pk = pk.replace("\r\n", "\n").replace("\r", "\n")
        if pk.count("\n") < 3:
            try:
                _, after_begin = pk.split("-----BEGIN PRIVATE KEY-----", 1)
                body, _ = after_begin.split("-----END PRIVATE KEY-----", 1)
                body = "".join(body.split())
                chunks = [body[i:i + 64] for i in range(0, len(body), 64)]
                pk = (
                    "-----BEGIN PRIVATE KEY-----\n"
                    + "\n".join(chunks)
                    + "\n-----END PRIVATE KEY-----\n"
                )
            except Exception:
                pass
        if not pk.endswith("\n"):
            pk += "\n"
        return pk

    def _load_credentials_dict():
        try:
            raw = st.secrets.get("gcp_service_account_json")
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = _normalise_private_key(creds_dict.get("private_key", ""))
        return creds_dict

    @st.cache_resource(show_spinner=False)
    def _get_worksheet():
        creds_dict = _load_credentials_dict()
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(st.secrets["sheet_id"])
        return sh.sheet1

    def init_db() -> None:
        with _LOCK:
            ws = _get_worksheet()
            try:
                first_row = ws.row_values(1)
            except Exception:
                first_row = []
            if first_row != HEADERS and not first_row:
                ws.update("A1", [HEADERS])

    def _next_id(ws) -> int:
        try:
            ids = ws.col_values(1)[1:]
            nums = [int(x) for x in ids if str(x).isdigit()]
            return (max(nums) + 1) if nums else 1
        except Exception:
            return 1

    def save_response(payload: dict) -> int:
        init_db()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
        with _LOCK:
            ws = _get_worksheet()
            new_id = _next_id(ws)
            row = [
                new_id, now,
                str(payload.get("general__cluster_name", "")),
                str(payload.get("general__cluster_product", "")),
                str(payload.get("general__cluster_geo", "")),
                str(payload.get("general__respondent", "")),
                str(payload.get("general__respondent_contact", "")),
                json.dumps(payload, ensure_ascii=False, default=str),
            ]
            ws.append_row(row, value_input_option="USER_ENTERED")
            return int(new_id)

    def list_responses() -> pd.DataFrame:
        init_db()
        with _LOCK:
            ws = _get_worksheet()
            try:
                records = ws.get_all_records()
            except Exception:
                records = []
        cols = ["id", "submitted_at", "cluster_name", "cluster_product",
                "cluster_geo", "respondent", "respondent_contact"]
        if not records:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(records)
        present = [c for c in cols if c in df.columns]
        df = df[present]
        if "id" in df.columns:
            df = df.sort_values("id", ascending=False)
        return df

    def get_response(response_id: int):
        with _LOCK:
            ws = _get_worksheet()
            try:
                records = ws.get_all_records()
            except Exception:
                records = []
        for r in records:
            if str(r.get("id")) == str(response_id):
                data = dict(r)
                try:
                    data["payload"] = json.loads(data.pop("payload_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    data["payload"] = {}
                return data
        return None

    def delete_response(response_id: int) -> None:
        with _LOCK:
            ws = _get_worksheet()
            try:
                records = ws.get_all_records()
            except Exception:
                return
            for i, r in enumerate(records):
                if str(r.get("id")) == str(response_id):
                    ws.delete_rows(i + 2)
                    return

    def export_dataframe() -> pd.DataFrame:
        init_db()
        with _LOCK:
            ws = _get_worksheet()
            try:
                records = ws.get_all_records()
            except Exception:
                records = []
        if not records:
            return pd.DataFrame()
        rows = []
        for r in records:
            try:
                payload = json.loads(r.get("payload_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                payload = {}
            flat = {}
            for k, v in payload.items():
                if isinstance(v, list):
                    flat[k] = " | ".join(str(x) for x in v)
                elif isinstance(v, dict):
                    flat[k] = json.dumps(v, ensure_ascii=False)
                else:
                    flat[k] = v
            flat["id"] = r.get("id")
            flat["submitted_at"] = r.get("submitted_at")
            rows.append(flat)
        df = pd.DataFrame(rows)
        front = ["id", "submitted_at"]
        cols = front + [c for c in df.columns if c not in front]
        return df[cols]


# ═══════════════════════════════════════════════════════════════════
# NO BACKEND CONFIGURED
# ═══════════════════════════════════════════════════════════════════
else:
    _ERR = (
        "No persistence backend is configured.\n\n"
        "Configure ONE of the following in `.streamlit/secrets.toml` "
        "(or as environment variables):\n\n"
        "  • MongoDB (preferred):  mongodb_uri = \"mongodb+srv://USER:PASS@CLUSTER/...\"\n"
        "  • Google Sheets:        sheet_id = \"...\" + gcp_service_account_json = '{...}'\n"
    )

    def init_db() -> None:
        raise RuntimeError(_ERR)

    def save_response(payload: dict) -> int:
        raise RuntimeError(_ERR)

    def list_responses() -> pd.DataFrame:
        raise RuntimeError(_ERR)

    def get_response(response_id: int):
        raise RuntimeError(_ERR)

    def delete_response(response_id: int) -> None:
        raise RuntimeError(_ERR)

    def export_dataframe() -> pd.DataFrame:
        raise RuntimeError(_ERR)
