"""
NICDC Legacy Industrial Cluster Questionnaire — Streamlit app.

Public page  : multi-section form, validates required fields, submits to SQLite.
Admin page   : password-gated dashboard to view, filter, download (CSV / XLSX / JSON)
               and delete individual responses.

Run locally  : `streamlit run app.py`
Deploy       : push to GitHub -> Streamlit Community Cloud -> set admin password
               in `Secrets` (key: `admin_password`).
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from questions import SECTIONS
from storage import (
    delete_response,
    export_dataframe,
    get_response,
    init_db,
    list_responses,
    save_response,
)

# ───────────────────────────── Page / theme setup ──────────────────────────────

ASSETS = Path(__file__).parent / "assets"


def _load_logo_html() -> str:
    """Prefer official PNG / JPG if present, fall back to SVG."""
    for fname in ("logo.png", "logo.jpg", "logo.jpeg"):
        f = ASSETS / fname
        if f.exists():
            ext = f.suffix.lower().lstrip(".")
            mime = "jpeg" if ext in ("jpg", "jpeg") else ext
            data = base64.b64encode(f.read_bytes()).decode("ascii")
            return (
                f'<img src="data:image/{mime};base64,{data}" alt="NICDC" '
                f'style="height:120px;width:auto;display:block;"/>'
            )
    svg = ASSETS / "logo.svg"
    if svg.exists():
        return svg.read_text(encoding="utf-8")
    return ""


LOGO_HTML = _load_logo_html()

st.set_page_config(
    page_title="NICDC · Legacy Industrial Cluster Questionnaire",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# NICDC brand palette
NAVY        = "#0B2545"
NAVY_DEEP   = "#08203E"
NAVY_SOFT   = "#13315C"
SAFFRON     = "#E87722"
SAFFRON_LT  = "#F4A024"
GOLD        = "#D4A017"
GREEN       = "#1F7A4D"
BG_SOFT     = "#F5F7FA"
BORDER      = "#DCE3EE"
TEXT_DARK   = "#0E1B2C"
TEXT_MUTED  = "#5A6B82"
LETTERHEAD  = "#C25932"   # burnt-orange used in NICDC letterhead wordmark
LOGO_RED    = "#9A3324"   # burgundy used in NICDC tree-logo lettering

CSS = f"""
<style>
:root {{
    --nicdc-navy: {NAVY};
    --nicdc-navy-soft: {NAVY_SOFT};
    --nicdc-saffron: {SAFFRON};
    --nicdc-gold: {GOLD};
    --nicdc-bg: {BG_SOFT};
    --nicdc-border: {BORDER};
}}

html, body, [class*="css"]  {{
    font-family: 'Segoe UI','Inter','Helvetica Neue',Arial,sans-serif;
    color: {TEXT_DARK};
}}

/* ── Hide ALL default Streamlit chrome ── */
#MainMenu                              {{display: none !important;}}
footer                                 {{display: none !important;}}
header[data-testid="stHeader"]         {{display: none !important; height: 0 !important;}}
[data-testid="stToolbar"]              {{display: none !important;}}
[data-testid="stToolbarActions"]       {{display: none !important;}}
[data-testid="stDecoration"]           {{display: none !important;}}
[data-testid="stStatusWidget"]         {{display: none !important;}}
[data-testid="stDeployButton"]         {{display: none !important;}}
[data-testid="stActionButton"]         {{display: none !important;}}
[data-testid="stAppViewBlockContainer"]{{padding-top: 1.2rem !important;}}
.viewerBadge_container__1QSob          {{display: none !important;}}
.styles_viewerBadge__1yB5_             {{display: none !important;}}
.stAppDeployButton                     {{display: none !important;}}
div[class*="viewerBadge"]              {{display: none !important;}}
a[href^="#"][class*="anchor"]          {{display: none !important;}}

.stApp {{
    background:
        radial-gradient(1100px 480px at 0% -10%, rgba(232,119,34,0.06), transparent 60%),
        radial-gradient(900px 420px at 100% 0%, rgba(11,37,69,0.07), transparent 55%),
        {BG_SOFT};
}}

/* ── Centered logo header ─────────────────────── */
.nicdc-header {{
    text-align: center;
    margin: 4px 0 26px;
    padding: 14px 0 6px;
}}
.nicdc-header .logo-wrap {{
    display: flex;
    justify-content: center;
    margin-bottom: 18px;
}}
.nicdc-header .logo-wrap img,
.nicdc-header .logo-wrap svg {{
    height: 170px; width: auto; display: block;
}}
.nicdc-header h1.header-title {{
    margin: 0 auto 6px;
    color: {LETTERHEAD};
    font-weight: 900;
    font-size: 28px;
    line-height: 1.25;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    text-decoration: underline;
    text-decoration-color: {LETTERHEAD};
    text-decoration-thickness: 2.5px;
    text-underline-offset: 6px;
    font-family: 'Arial Black','Helvetica Neue',Arial,sans-serif;
}}
.nicdc-header .page-title {{
    margin-top: 14px;
    color: {NAVY};
    font-weight: 800;
    font-size: 19px;
    letter-spacing: 0.3px;
}}
.nicdc-header .page-title .accent {{ color: {LETTERHEAD}; }}

/* ── Section cards ─────────────────────────────────────────────────── */
.section-card {{
    background: #FFFFFF;
    border: 1px solid {BORDER};
    border-left: 5px solid {SAFFRON};
    border-radius: 12px;
    padding: 18px 22px 4px;
    margin-bottom: 14px;
    box-shadow: 0 1px 2px rgba(11,37,69,0.04);
}}
.section-card h3 {{
    margin: 0 0 4px;
    color: {NAVY};
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.2px;
}}
.section-card .section-sub {{
    color: {TEXT_MUTED};
    font-size: 13px;
    margin-bottom: 12px;
}}

/* ── Info callout ──────────────────────────────────────────────────── */
.info-callout {{
    background: #FFF5EB;
    border-left: 4px solid {SAFFRON};
    color: #6B3A0E;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 13.5px;
    margin: 6px 0 14px;
}}

/* ── Inputs / labels ───────────────────────────────────────────────── */
label, .stRadio label, .stCheckbox label {{ color: {TEXT_DARK} !important; font-weight: 600; }}
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {{
    border-radius: 8px !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, {SAFFRON} 0%, {GOLD} 100%);
    color: #FFFFFF;
    border: 0;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 700;
    letter-spacing: 0.3px;
    box-shadow: 0 6px 14px rgba(232,119,34,0.25);
}}
.stButton > button:hover {{ filter: brightness(1.05); }}
.stDownloadButton > button {{
    background: {NAVY};
    color: #FFFFFF;
    border: 0;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
}}

/* ── Sidebar ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {NAVY_DEEP} 0%, {NAVY} 100%);
}}
[data-testid="stSidebar"] * {{ color: #E9EEF7; }}
[data-testid="stSidebar"] .stRadio label {{ color: #E9EEF7 !important; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: {SAFFRON_LT}; }}
[data-testid="stSidebar"] .sidebar-card {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    padding: 12px;
    margin-top: 10px;
    font-size: 12.5px;
    line-height: 1.5;
}}

/* ── Stats / pills ─────────────────────────────────────────────────── */
.kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 14px; }}
.kpi {{
    background: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 12px 16px;
    min-width: 160px;
    box-shadow: 0 1px 2px rgba(11,37,69,0.04);
}}
.kpi .label {{ font-size: 11.5px; color: {TEXT_MUTED}; letter-spacing: 1px; text-transform: uppercase; font-weight: 700;}}
.kpi .value {{ font-size: 24px; color: {NAVY}; font-weight: 800; }}

/* ── Success banner ───────────────────────────────────────────────── */
.success-banner {{
    background: linear-gradient(135deg, #E9F8F0 0%, #D7F1E2 100%);
    border-left: 5px solid {GREEN};
    color: #094B2B;
    padding: 14px 18px;
    border-radius: 10px;
    font-weight: 600;
}}

/* ── Footer (custom) ─────────────────────────────────────────────── */
.nicdc-footer {{
    margin-top: 36px;
    padding: 14px 0;
    border-top: 1px solid {BORDER};
    text-align: center;
    color: {TEXT_MUTED};
    font-size: 12.5px;
}}
.nicdc-footer strong {{ color: {NAVY}; }}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ───────────────────────────── Helpers ─────────────────────────────

def render_banner(subtitle: str = "") -> None:
    """Centered NICDC header — logo on top, bold orange underlined wordmark below."""
    banner_html = f"""
    <div class="nicdc-header">
        <div class="logo-wrap">{LOGO_HTML}</div>
        <h1 class="header-title">National Industrial Corridor<br/>Development Corporation</h1>
        <div class="page-title">Legacy Industrial Cluster <span class="accent">Questionnaire</span></div>
    </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)


def section_header(section: dict) -> None:
    instr = section.get("instructions", "")
    sub = f'<div class="section-sub">{instr}</div>' if instr else ""
    st.markdown(
        f'<div class="section-card"><h3>{section.get("icon","")} {section["title"]}</h3>{sub}</div>',
        unsafe_allow_html=True,
    )


def get_admin_password() -> str:
    """Resolve admin password from Streamlit secrets, else env var, else default."""
    try:
        if "admin_password" in st.secrets:
            return str(st.secrets["admin_password"])
    except (FileNotFoundError, RuntimeError, KeyError):
        pass
    import os
    return os.getenv("NICDC_ADMIN_PASSWORD", "NICDC@11444")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="nicdc-footer">
            © {datetime.utcnow().year} <strong>National Industrial Corridor Development Corporation Ltd.</strong>
            · Legacy Industrial Cluster Questionnaire Portal
        </div>
        """,
        unsafe_allow_html=True,
    )


# ───────────────────────────── Form widgets ────────────────────────────

def _render_question(q: dict, key_prefix: str, container) -> object:
    """Render one question and return its value (or None for `info`)."""
    qid = q["id"]
    qtype = q["type"]
    key = f"{key_prefix}__{qid}"
    label = q["label"] + (" *" if q.get("required") else "")

    if qtype == "info":
        container.markdown(f'<div class="info-callout">{q["label"]}</div>', unsafe_allow_html=True)
        return None

    if qtype == "text":
        return container.text_input(label, key=key, value=st.session_state.get(key, ""))

    if qtype == "textarea":
        height = q.get("height", 110)
        return container.text_area(label, key=key, height=height, value=st.session_state.get(key, ""))

    if qtype == "number":
        return container.number_input(
            label, key=key,
            min_value=q.get("min", 0),
            max_value=q.get("max", None),
            step=q.get("step", 1),
            value=st.session_state.get(key, q.get("min", 0)),
        )

    if qtype == "yesno":
        return container.radio(label, options=["Yes", "No"], key=key, horizontal=True, index=None)

    if qtype == "select":
        opts = q["options"]
        return container.selectbox(label, options=["— Select —"] + opts, key=key)

    if qtype == "multiselect":
        opts = q["options"]
        return container.multiselect(label, options=opts, key=key)

    if qtype == "rank":
        container.markdown(f"**{label}**")
        opts = q["options"]
        chosen = container.multiselect("Select applicable challenges", options=opts, key=f"{key}__sel")
        ranks: dict = {}
        if chosen:
            cols = container.columns(min(len(chosen), 4))
            for i, opt in enumerate(chosen):
                with cols[i % len(cols)]:
                    ranks[opt] = st.number_input(
                        f"Rank — {opt}", min_value=1, max_value=len(opts),
                        step=1, key=f"{key}__rank__{i}", value=i + 1,
                    )
        return {"selected": chosen, "ranks": ranks}

    container.warning(f"Unhandled type: {qtype}")
    return None


def _render_repeat(q: dict, section_id: str, container) -> dict:
    block_label = q.get("block_label", "Block")
    max_blocks = q.get("max_blocks", 3)
    min_blocks = q.get("min_blocks", 1)
    count_key = f"{section_id}__{q['id']}__count"
    if count_key not in st.session_state:
        st.session_state[count_key] = min_blocks

    c1, c2, _ = container.columns([1, 1, 6])
    if c1.button(f"➕ Add {block_label}", key=f"{count_key}__add",
                 disabled=st.session_state[count_key] >= max_blocks):
        st.session_state[count_key] = min(max_blocks, st.session_state[count_key] + 1)
    if c2.button(f"➖ Remove last", key=f"{count_key}__rm",
                 disabled=st.session_state[count_key] <= min_blocks):
        st.session_state[count_key] = max(min_blocks, st.session_state[count_key] - 1)

    blocks_data = {}
    for b in range(1, st.session_state[count_key] + 1):
        with container.expander(f"{block_label} {b}", expanded=(b == 1)):
            block = {}
            for f in q["fields"]:
                block[f["id"]] = _render_question(
                    f, key_prefix=f"{section_id}__{q['id']}__b{b}", container=st
                )
            blocks_data[f"b{b}"] = block
    return blocks_data


# ─────────────────────────── PUBLIC: Form page ────────────────────────

def page_form() -> None:
    render_banner()

    st.markdown(
        f"""
        <div class="info-callout">
            <strong>Purpose:</strong> This survey assesses the existing ecosystem of industrial clusters —
            their contribution to employment, income generation, value addition, and overall economic development —
            and identifies challenges, solutions, and stakeholder priorities to inform the proposed
            <em>cluster revitalisation programme</em>.<br/>
            <strong>Disclaimer:</strong> Responses are confidential and used solely for research and policy support.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "submitted_payload_id" not in st.session_state:
        st.session_state["submitted_payload_id"] = None

    collected: dict = {}
    for section in SECTIONS:
        section_header(section)
        with st.container():
            for q in section["questions"]:
                if q["type"] == "repeat":
                    collected[f"{section['id']}__{q['id']}"] = _render_repeat(q, section["id"], st)
                elif q["type"] == "info":
                    _render_question(q, key_prefix=section["id"], container=st)
                else:
                    collected[f"{section['id']}__{q['id']}"] = _render_question(
                        q, key_prefix=section["id"], container=st
                    )

    st.markdown("---")
    col_a, col_b = st.columns([1, 3])
    with col_a:
        submitted = st.button(
            "✅ Submit Response", use_container_width=True,
            type="primary", key="nicdc_submit_btn",
        )
    with col_b:
        st.caption(
            "By submitting, you confirm that the information provided is accurate "
            "to the best of your knowledge."
        )

    if submitted:
        # Required-field validation
        missing = []
        for section in SECTIONS:
            for q in section["questions"]:
                if q.get("required"):
                    val = collected.get(f"{section['id']}__{q['id']}")
                    if val in (None, "", "— Select —"):
                        missing.append(q["label"])
        if missing:
            st.error("Please complete the required fields:\n\n- " + "\n- ".join(missing))
            return

        # Normalise sentinel select values
        for k, v in list(collected.items()):
            if v == "— Select —":
                collected[k] = ""

        new_id = save_response(collected)
        st.session_state["submitted_payload_id"] = new_id
        st.markdown(
            f'<div class="success-banner">✅ Thank you. Your response has been recorded. '
            f'Reference ID: <strong>NICDC-{new_id:05d}</strong></div>',
            unsafe_allow_html=True,
        )
        st.balloons()


# ─────────────────────────── ADMIN page ──────────────────────────────

def page_admin() -> None:
    render_banner()
    st.markdown(
        '<div style="text-align:center;color:#5A6B82;font-size:14px;margin:-8px 0 18px;">'
        'Administrator Dashboard · view, filter and export survey responses</div>',
        unsafe_allow_html=True,
    )

    if "admin_authed" not in st.session_state:
        st.session_state["admin_authed"] = False

    if not st.session_state["admin_authed"]:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            with st.form("login"):
                st.subheader("🔐 Administrator Login")
                pw = st.text_input("Admin password", type="password")
                ok = st.form_submit_button("Sign in", use_container_width=True)
            if ok:
                if _hash(pw) == _hash(get_admin_password()):
                    st.session_state["admin_authed"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            st.caption(
                "Password is set via Streamlit secrets (`admin_password`) "
                "or env var `NICDC_ADMIN_PASSWORD`."
            )
        return

    # Authenticated view
    df = list_responses()
    total = len(df)
    today = sum(
        1 for _, r in df.iterrows()
        if str(r.get("submitted_at", "")).startswith(datetime.utcnow().strftime("%Y-%m-%d"))
    )
    unique_clusters = df["cluster_name"].nunique() if total else 0

    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi"><div class="label">Total Responses</div><div class="value">{total}</div></div>
            <div class="kpi"><div class="label">Submitted Today (UTC)</div><div class="value">{today}</div></div>
            <div class="kpi"><div class="label">Unique Clusters</div><div class="value">{unique_clusters}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if total == 0:
        st.info("No responses submitted yet.")
        st.markdown("---")
        if st.button("Sign out"):
            st.session_state["admin_authed"] = False
            st.rerun()
        return

    # Search + filter
    q = st.text_input("🔎 Search (cluster name, product, location, respondent)")
    df_view = df.copy()
    if q:
        ql = q.strip().lower()
        df_view = df_view[df_view.apply(
            lambda r: ql in " ".join(
                str(r[c]).lower()
                for c in ["cluster_name", "cluster_product", "cluster_geo", "respondent"]
            ),
            axis=1,
        )]

    st.dataframe(df_view, use_container_width=True, hide_index=True)

    # Exports
    st.markdown("### ⬇️ Export")
    full = export_dataframe()
    if not full.empty:
        csv = full.to_csv(index=False).encode("utf-8")
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            full.to_excel(writer, index=False, sheet_name="Responses")
        json_bytes = full.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "⬇ CSV", csv,
            file_name=f"nicdc_responses_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        c2.download_button(
            "⬇ Excel", xlsx_buf.getvalue(),
            file_name=f"nicdc_responses_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        c3.download_button(
            "⬇ JSON", json_bytes,
            file_name=f"nicdc_responses_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("### 🔍 Inspect / Delete a Response")
    selected_id = st.selectbox("Select response ID", options=df_view["id"].tolist())
    if selected_id:
        record = get_response(int(selected_id))
        if record is not None:
            meta = {k: v for k, v in record.items() if k != "payload"}
            st.markdown(
                f"**Submitted at:** {meta.get('submitted_at')}  ·  "
                f"**Cluster:** {meta.get('cluster_name')}  ·  "
                f"**Respondent:** {meta.get('respondent')}"
            )

            # Pretty-print by section
            with st.expander("🧾 Section-wise view", expanded=True):
                for section in SECTIONS:
                    rows = []
                    for q in section["questions"]:
                        if q["type"] == "info":
                            continue
                        key = f"{section['id']}__{q['id']}"
                        val = record["payload"].get(key, "")
                        if isinstance(val, list):
                            val = ", ".join(str(x) for x in val) or "—"
                        elif isinstance(val, dict):
                            val = json.dumps(val, ensure_ascii=False)
                        elif val in (None, ""):
                            val = "—"
                        rows.append({"Question": q["label"], "Answer": val})
                    if rows:
                        st.markdown(f"**{section.get('icon','')} {section['title']}**")
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            with st.expander("📑 Full payload (JSON)", expanded=False):
                st.json(record["payload"])

            # Per-response download
            single_json = json.dumps(record, ensure_ascii=False, indent=2, default=str).encode("utf-8")
            st.download_button(
                f"⬇ Download response NICDC-{int(selected_id):05d} (JSON)",
                single_json,
                file_name=f"nicdc_response_{int(selected_id):05d}.json",
                mime="application/json",
            )

            colx, _ = st.columns([1, 5])
            if colx.button("🗑 Delete this response", type="secondary"):
                delete_response(int(selected_id))
                st.success(f"Response {selected_id} deleted.")
                st.rerun()

    st.markdown("---")
    if st.button("Sign out"):
        st.session_state["admin_authed"] = False
        st.rerun()


# ───────────────────────────── App entry point ─────────────────────────

def main() -> None:
    init_db()

    # Sidebar — branded nav
    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align:center;padding:8px 0 14px;">
                <div style="font-size:22px;font-weight:900;color:{SAFFRON_LT};letter-spacing:2px;">NICDC</div>
                <div style="font-size:11px;color:#C9D2E0;letter-spacing:1px;margin-top:2px;">
                    NATIONAL INDUSTRIAL<br/>CORRIDOR DEV. CORP.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### Navigation")
        page = st.radio(
            "Choose a page",
            ["📝 Fill Questionnaire", "🛠 Administrator"],
            label_visibility="collapsed",
            key="nicdc_page",
        )

        st.markdown(
            """
            <div class="sidebar-card">
                <strong>About this portal</strong><br/>
                Captures the Legacy Industrial Cluster Questionnaire from
                associations &amp; stakeholders.<br/><br/>
                Responses are stored securely and accessible only to
                authorised administrators for analysis &amp; export.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="sidebar-card" style="margin-top:14px;">
                <strong>Contact &amp; Support</strong><br/>
                For queries on this survey, please write to the
                cluster programme team at NICDC.
            </div>
            <div style="margin-top:16px;text-align:center;font-size:11px;color:#8B97AB;">
                v1.0 · © {datetime.utcnow().year} NICDC
            </div>
            """,
            unsafe_allow_html=True,
        )

    if page.startswith("📝"):
        page_form()
    else:
        page_admin()

    render_footer()


if __name__ == "__main__":
    main()
