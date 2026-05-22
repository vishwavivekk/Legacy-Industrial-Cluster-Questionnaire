"""SQLite-backed persistence layer for the questionnaire."""
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

DB_LOCK = threading.Lock()
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("NICDC_DB_PATH", DB_DIR / "responses.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


@contextmanager
def get_conn():
    with DB_LOCK:
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


def save_response(payload: dict[str, Any]) -> int:
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
        df = pd.read_sql_query(
            "SELECT id, submitted_at, cluster_name, cluster_product, cluster_geo, "
            "respondent, respondent_contact FROM responses ORDER BY id DESC",
            conn,
        )
    return df


def get_response(response_id: int) -> dict[str, Any] | None:
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
    """Wide-format dataframe: one row per response, one column per question id."""
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
        # Flatten list-typed answers into pipe-separated strings for tabular export.
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
    # Move id + submitted_at to the front.
    front = ["id", "submitted_at"]
    cols = front + [c for c in df.columns if c not in front]
    return df[cols]
