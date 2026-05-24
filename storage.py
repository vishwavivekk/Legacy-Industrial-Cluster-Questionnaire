"""
MongoDB persistence layer.

Configuration (st.secrets or environment variables):
    mongodb_uri         (required)  e.g. mongodb+srv://USER:PASS@host/...
    mongodb_db          (optional)  defaults to "nicdc"
    mongodb_collection  (optional)  defaults to "responses"
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError


_LOCK = threading.Lock()


def _secret(name: str, default: Any = None) -> Any:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except (FileNotFoundError, RuntimeError, KeyError):
        pass
    return os.getenv(name.upper(), default)


def _uri() -> str:
    uri = _secret("mongodb_uri") or os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MongoDB is not configured. Set `mongodb_uri` in "
            ".streamlit/secrets.toml or export MONGODB_URI."
        )
    return str(uri)


DB_NAME = str(_secret("mongodb_db", "nicdc"))
COLL_NAME = str(_secret("mongodb_collection", "responses"))
COUNTER_COLL = "counters"


@st.cache_resource(show_spinner=False)
def _get_client() -> "MongoClient":
    client = MongoClient(_uri(), serverSelectionTimeoutMS=10000, appname="nicdc-questionnaire")
    client.admin.command("ping")
    return client


def _coll():
    return _get_client()[DB_NAME][COLL_NAME]


def _counters():
    return _get_client()[DB_NAME][COUNTER_COLL]


def _next_id() -> int:
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


_SUMMARY_COLS = ["id", "submitted_at", "cluster_name", "cluster_product",
                 "cluster_geo", "respondent", "respondent_contact"]


def list_responses() -> pd.DataFrame:
    init_db()
    with _LOCK:
        cursor = _coll().find({}, projection={"_id": 0, "payload": 0}).sort("id", -1)
        rows = list(cursor)
    if not rows:
        return pd.DataFrame(columns=_SUMMARY_COLS)
    df = pd.DataFrame(rows)
    for c in _SUMMARY_COLS:
        if c not in df.columns:
            df[c] = ""
    return df[_SUMMARY_COLS]


def get_response(response_id: int):
    with _LOCK:
        doc = _coll().find_one({"id": int(response_id)}, projection={"_id": 0})
    if doc is None:
        return None
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
