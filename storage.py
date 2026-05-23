"""
Persistence layer with automatic backend selection:
  - Google Sheets if st.secrets has either `gcp_service_account_json` (preferred)
    or a `[gcp_service_account]` table AND `sheet_id`.
  - Local SQLite fallback otherwise. The app always loads; you'll only lose
    persistence if Sheets isn't configured.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ─── Backend detection ───────────────────────────────────────────────
_USE_SHEETS = False
try:
    if "sheet_id" in st.secrets and (
        st.secrets.get("gcp_service_account_json")
        or "gcp_service_account" in st.secrets
    ):
        # Try importing gspread; if it isn't installed, fall through to SQLite
        import gspread
        from google.oauth2.service_account import Credentials
        _USE_SHEETS = True
except Exception:
    _USE_SHEETS = False


_LOCK = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
# GOOGLE SHEETS BACKEND
# ═══════════════════════════════════════════════════════════════════
if _USE_SHEETS:
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
        # Preferred: single JSON string in secrets
        try:
            raw = st.secrets.get("gcp_service_account_json")
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        # Legacy: TOML table
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
# SQLITE FALLBACK (used if Sheets isn't configured)
# ═══════════════════════════════════════════════════════════════════
else:
    DB_DIR = Path(__file__).parent / "data"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = Path(os.getenv("NICDC_DB_PATH", DB_DIR / "responses.db"))

    def _connect():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    @contextmanager
    def get_conn():
        with _LOCK:
            conn = _connect()
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def init_db() -> None:
        with get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    submitted_at    TEXT    NOT NULL,
                    cluster_name    TEXT,
                    cluster_product TEXT,
                    cluster_geo     TEXT,
                    respondent      TEXT,
                    respondent_contact TEXT,
                    payload_json    TEXT    NOT NULL
                )
                """
            )

    def save_response(payload: dict) -> int:
        init_db()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
        with get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO responses
                    (submitted_at, cluster_name, cluster_product, cluster_geo,
                     respondent, respondent_contact, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    str(payload.get("general__cluster_name", "")),
                    str(payload.get("general__cluster_product", "")),
                    str(payload.get("general__cluster_geo", "")),
                    str(payload.get("general__respondent", "")),
                    str(payload.get("general__respondent_contact", "")),
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )
            return int(cur.lastrowid)

    def list_responses() -> pd.DataFrame:
        init_db()
        with get_conn() as conn:
            return pd.read_sql_query(
                "SELECT id, submitted_at, cluster_name, cluster_product, cluster_geo, "
                "respondent, respondent_contact FROM responses ORDER BY id DESC",
                conn,
            )

    def get_response(response_id: int):
        init_db()
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM responses WHERE id = ?", (response_id,)
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        try:
            data["payload"] = json.loads(data.pop("payload_json"))
        except (json.JSONDecodeError, TypeError):
            data["payload"] = {}
        return data

    def delete_response(response_id: int) -> None:
        init_db()
        with get_conn() as conn:
            conn.execute("DELETE FROM responses WHERE id = ?", (response_id,))

    def export_dataframe() -> pd.DataFrame:
        init_db()
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, submitted_at, payload_json FROM responses ORDER BY id"
            ).fetchall()
        records = []
        for r in rows:
            try:
                payload = json.loads(r["payload_json"])
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
            flat["id"] = r["id"]
            flat["submitted_at"] = r["submitted_at"]
            records.append(flat)
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        front = ["id", "submitted_at"]
        cols = front + [c for c in df.columns if c not in front]
        return df[cols]
