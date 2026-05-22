"""
Google-Sheets-backed persistence layer.

Reads / writes responses to the spreadsheet whose ID is in st.secrets["sheet_id"],
authenticating with the service-account credentials in st.secrets["gcp_service_account"].

Public API (unchanged from the SQLite version, so app.py needs no edits):
    init_db()              - ensure header row exists
    save_response(payload) - append row, return new id
    list_responses()       - DataFrame of metadata
    get_response(id)       - dict with metadata + parsed payload
    delete_response(id)    - delete row by id
    export_dataframe()     - wide-format DataFrame (1 column per question id)
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

import gspread
from google.oauth2.service_account import Credentials

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

_LOCK = threading.Lock()


def _normalise_private_key(pk: str) -> str:
    """
    Ensure the private_key string is a valid PEM block with real newlines.
    Handles three common bad cases from TOML pasting:
      1. Literal "\\n" (backslash-n) instead of real newlines.
      2. Single long line with no separators at all (newlines stripped).
      3. CRLF or extra whitespace from copy-paste.
    """
    if not isinstance(pk, str) or "BEGIN PRIVATE KEY" not in pk:
        return pk
    # Case 1: convert literal "\n" sequences into real newlines
    if "\\n" in pk:
        pk = pk.replace("\\n", "\n")
    # Case 3: normalise CRLF
    pk = pk.replace("\r\n", "\n").replace("\r", "\n")
    # Case 2: if still no newlines inside the body, reconstruct PEM with 64-char chunks
    if pk.count("\n") < 3:
        try:
            _, after_begin = pk.split("-----BEGIN PRIVATE KEY-----", 1)
            body, _ = after_begin.split("-----END PRIVATE KEY-----", 1)
            body = "".join(body.split())  # strip ALL whitespace
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


@st.cache_resource(show_spinner=False)
def _get_worksheet():
    """Authenticate once per session and return the responses worksheet."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = _normalise_private_key(creds_dict.get("private_key", ""))
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["sheet_id"])
    return sh.sheet1


def init_db() -> None:
    """Ensure the header row exists (idempotent)."""
    with _LOCK:
        ws = _get_worksheet()
        try:
            first_row = ws.row_values(1)
        except Exception:
            first_row = []
        if first_row != HEADERS:
            if not first_row:
                ws.update("A1", [HEADERS])
            # If a different header exists, leave it alone — admin can clean up.


def _next_id(ws) -> int:
    """Compute next response id as max(existing ids) + 1."""
    try:
        ids = ws.col_values(1)[1:]  # skip header row
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
            new_id,
            now,
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
    cols_to_show = [
        "id", "submitted_at",
        "cluster_name", "cluster_product", "cluster_geo",
        "respondent", "respondent_contact",
    ]
    if not records:
        return pd.DataFrame(columns=cols_to_show)
    df = pd.DataFrame(records)
    present = [c for c in cols_to_show if c in df.columns]
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
        # Row 1 is header, so data records start at row 2 (i + 2 below)
        for i, r in enumerate(records):
            if str(r.get("id")) == str(response_id):
                ws.delete_rows(i + 2)
                return


def export_dataframe() -> pd.DataFrame:
    """Wide-format: one row per response, one column per question id."""
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
