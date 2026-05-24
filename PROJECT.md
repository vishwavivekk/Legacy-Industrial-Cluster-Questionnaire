# NICDC · Legacy Industrial Cluster Questionnaire — Project Documentation

A Streamlit web application that captures the **National Industrial Corridor Development Corporation (NICDC) Legacy Industrial Cluster Questionnaire** from industry-association respondents and provides a password-gated administrator dashboard to view, search, inspect, and export responses.

---

## 1. Purpose

The portal supports NICDC's proposed **cluster revitalisation programme**. It surveys legacy industrial clusters across India to assess:

- Their contribution to employment, income generation and value addition
- Existing ecosystem (associations, BDS, infrastructure, industrial parks)
- Challenges across raw material, machinery, finance, energy/water, HR, waste
- Stakeholder priorities and suggested interventions

Responses are treated as confidential and used solely for research and policy support.

---

## 2. High-level Architecture

```
                ┌──────────────────────────────────┐
                │        Streamlit UI (app.py)     │
                │  ┌──────────────┐ ┌────────────┐ │
                │  │ Public Form  │ │   Admin    │ │
                │  │  page_form() │ │ page_admin │ │
                │  └──────┬───────┘ └─────┬──────┘ │
                └─────────┼───────────────┼────────┘
                          │               │
              ┌───────────▼───────────────▼──────────┐
              │           questions.py               │
              │  SECTIONS schema (16 sections, ~85   │
              │  questions) — single source of truth │
              └──────────────────┬───────────────────┘
                                 │
              ┌──────────────────▼───────────────────┐
              │            storage.py                │
              │  Auto-selects backend:               │
              │  ┌─────────────┐  ┌────────────────┐ │
              │  │ Google      │  │ SQLite         │ │
              │  │ Sheets      │  │ (fallback)     │ │
              │  │ (gspread)   │  │ data/responses │ │
              │  └─────────────┘  └────────────────┘ │
              └──────────────────────────────────────┘
```

Three Python modules plus brand assets — no database server, no API layer. The schema in [questions.py](questions.py) drives both form rendering and export, so adding a question requires no UI code changes.

---

## 3. Repository Layout

```
Legacy-Industrial-Cluster-Questionnaire/
├── app.py              # Streamlit entry point — UI, theming, form + admin pages
├── questions.py        # SECTIONS schema (declarative form definition)
├── storage.py          # Persistence layer (Google Sheets ⇆ SQLite)
├── requirements.txt    # Python deps (streamlit, pandas, openpyxl, gspread, google-auth)
├── runtime.txt         # python-3.11 (Streamlit Cloud hint)
├── README.md           # Quick-start / deployment notes
├── assets/
│   └── logo.jpg        # NICDC branding (PNG/JPG preferred over SVG)
└── data/               # SQLite DB written here at runtime (gitignored)
```

---

## 4. Module Walkthrough

### 4.1 [app.py](app.py) — UI Layer

The single Streamlit entry point. Responsibilities:

| Concern | Where |
|---|---|
| Page config, theme, brand palette | top of file, `CSS` block |
| Logo loading (PNG/JPG → SVG fallback) | [`_load_logo_html`](app.py#L36) |
| Sidebar navigation (Form / Admin) | [`main`](app.py#L690) |
| Public form rendering | [`page_form`](app.py#L470) |
| Admin dashboard | [`page_admin`](app.py#L544) |
| Per-question widget dispatch | [`_render_question`](app.py#L385) |
| Repeat blocks (raw material, machinery) | [`_render_repeat`](app.py#L445) |
| Admin auth (SHA-256 compare) | [`get_admin_password`](app.py#L357), [`_hash`](app.py#L367) |

**Brand palette** (defined as Python constants): navy `#0B2545`, saffron `#E87722`, gold `#D4A017` — the "India Reimagined" identity.

**UI hardening** worth noting:
- All default Streamlit chrome (`MainMenu`, footer, share/deploy/embed buttons) is hidden via CSS.
- Sidebar is locked **always-open** — collapse button hidden, `transform`/`margin-left` forced.
- A small inline JS block (`components.html`) iterates the parent document and force-hides any leaked Streamlit Cloud "Share / Embed" popup.
- Form labels are forced dark (`#0E1B2C`) so they remain legible on the light theme — Streamlit's defaults wash out against the radial gradient background.

### 4.2 [questions.py](questions.py) — Schema

Single declarative source of truth. Each section is `{id, title, icon, instructions?, questions: [...]}`. Each question carries `id`, `label`, `type`, and type-specific extras.

Supported question types:

| Type | Widget | Notes |
|---|---|---|
| `text` | `st.text_input` | |
| `textarea` | `st.text_area` | optional `height` |
| `number` | `st.number_input` | `min` / `max` / `step` (int or float) |
| `yesno` | `st.radio` | horizontal, no default selection |
| `select` | `st.selectbox` | prepends `— Select —` sentinel |
| `multiselect` | `st.multiselect` | |
| `rank` | multiselect + per-item `number_input` | returns `{"selected": [...], "ranks": {opt: n}}` |
| `info` | static callout | no input, no key |
| `repeat` | expander blocks 1..`max_blocks` | nested `fields` rendered per block |

[`all_question_ids()`](questions.py#L283) flattens every leaf into the `section__qid` (or `section__qid__bN__field`) form used as payload keys.

**Sections (16)**:
General · A. Industry Association · B. Cluster Information · C. Support Firms/BDS · C.1 Infrastructure · C.2 Industrial Parks · C.3 Compliance · C.4 Value Chain / Export · C.5 Market Promotion · C.6 Raw Material (repeat ×3) · C.7 Machinery (repeat ×3) · C.8 Finance · C.9 Energy & Water · C.10 HR / Capacity Building · C.11 Waste Management · D. Conclusion.

### 4.3 [storage.py](storage.py) — Persistence

At import time it inspects `st.secrets`:

- If `sheet_id` **and** either `gcp_service_account_json` (raw JSON string) or `[gcp_service_account]` (TOML table) are present, **and** `gspread` imports cleanly → `_USE_SHEETS = True`.
- Otherwise → fall back to **SQLite** at `data/responses.db` (path overridable via `NICDC_DB_PATH`).

Both backends expose the same five functions:

| Function | Purpose |
|---|---|
| `init_db()` | Creates table / writes header row |
| `save_response(payload) -> int` | Inserts a row, returns new id |
| `list_responses() -> DataFrame` | Summary columns for the admin table |
| `get_response(id) -> dict\|None` | One row, with `payload` re-parsed from JSON |
| `delete_response(id)` | Hard-delete |
| `export_dataframe() -> DataFrame` | Flattened wide table for CSV/XLSX/JSON export |

**Sheet schema** (single worksheet, `sheet1`):
`id | submitted_at | cluster_name | cluster_product | cluster_geo | respondent | respondent_contact | payload_json`

**SQLite schema** mirrors the same columns. The full form payload is always stored as a JSON blob in `payload_json` — the dedicated columns are just denormalised summary fields used for the dashboard table and search.

**Private key normalisation** ([`_normalise_private_key`](storage.py#L55)) handles the common Streamlit Cloud failure mode where pasted service-account keys lose newlines: it converts `\n` literals back to real newlines, and if newlines are still missing it rebuilds the PEM by chunking the base64 body into 64-char lines.

A module-level `threading.Lock` guards all writes (Streamlit may handle concurrent sessions in the same process).

---

## 5. Data Flow

**Submission**:
1. User fills the form on the **Fill Questionnaire** page.
2. On submit, `page_form` walks `SECTIONS` again, builds a `collected` dict, and validates `required` fields. The select sentinel `— Select —` is treated as empty.
3. `save_response(collected)` writes to Sheets or SQLite, returns an integer id.
4. UI shows banner `NICDC-{id:05d}` and triggers `st.balloons()`.

**Admin viewing**:
1. Admin signs in (password from `st.secrets["admin_password"]` → env `NICDC_ADMIN_PASSWORD` → hardcoded `NICDC@11444`). Comparison uses SHA-256 hashes of both sides — defends against trivial timing leaks but is **not** a salted KDF; treat the password as low-sensitivity.
2. Dashboard renders three KPIs (total, today UTC, unique clusters), a searchable table, and an inspect/export panel.
3. Exports flatten the JSON payload column-wise (`list` → `"a | b | c"`, `dict` → JSON string) into CSV / XLSX / JSON.

---

## 6. Configuration

### Secrets (`.streamlit/secrets.toml` or Streamlit Cloud → Secrets)

```toml
admin_password = "NICDC@11444"

# --- For Google Sheets backend ---
sheet_id = "1AbCDeFgH..."     # the long key from the sheet URL

# Option A (preferred): paste the whole service-account JSON as a single string
gcp_service_account_json = """{ "type": "service_account", ... }"""

# Option B (legacy): TOML table — private_key newlines are auto-fixed
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@...iam.gserviceaccount.com"
# ...
```

The service account must have **Editor** access on the target Google Sheet (share the sheet with its `client_email`).

### Environment variables

| Variable | Purpose |
|---|---|
| `NICDC_ADMIN_PASSWORD` | Override admin password without secrets |
| `NICDC_DB_PATH` | Custom SQLite path (e.g. mount a persistent disk) |

---

## 7. Running Locally

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open <http://localhost:8501>. The sidebar offers **Fill Questionnaire** and **Administrator**.

Default admin password: `NICDC@11444`.

---

## 8. Deployment

The current production target is **Streamlit Community Cloud**.

- Sheets backend keeps responses persistent across the ephemeral filesystem resets that hit Cloud apps when they sleep / redeploy.
- If Sheets secrets are missing, the app still loads (recent commit `277da8f`: "Auto-fallback to SQLite when Sheets secrets are missing") — but persistence is best-effort on Cloud.
- For self-hosted deployments (Render, Railway, Fly.io, EC2, K8s) any Python host that exposes port 8501 works; mount a volume at `data/` if staying on SQLite.

---

## 9. Recent Git History (`main`)

```
277da8f Auto-fallback to SQLite when Sheets secrets are missing
284ca69 Normalise private_key newlines for Sheets auth
f31e2df Switch to Google Sheets backend for persistent storage
26d3307 Lock sidebar always-open, remove fragile toggle
4ef2ed4 Fix arrow button: stop navigating to share.streamlit.io, use sidebar-safe selectors
```

The trajectory has been: harden the Streamlit Cloud UX (kill share/embed chrome, lock sidebar), then move persistence off ephemeral disk to Google Sheets, then add graceful degradation when Sheets isn't configured.

---

## 10. Extending the App

| Task | Where |
|---|---|
| Add / edit / reorder a question | append to `SECTIONS` in [questions.py](questions.py) |
| Add a new question *type* | add a branch in [`_render_question`](app.py#L385) |
| Change theme colours | the brand-palette constants at the top of [app.py](app.py) and the `CSS` block |
| Replace the logo | drop `logo.png` / `logo.jpg` into [assets/](assets/) |
| Swap persistence backend | implement the five-function interface in [storage.py](storage.py) |
| Restrict admin access further | extend [`get_admin_password`](app.py#L357) / login form (SSO, IP allowlist, etc.) |

---

## 11. Known Limitations / Hardening TODO

- **Auth**: single shared admin password, SHA-256 compared — not a KDF, no rate limiting, no audit log. For multi-admin use, integrate `streamlit-authenticator` or an external IdP.
- **PII**: `respondent_contact` is stored in plain text in both Sheets and SQLite. Encrypt at rest if responses include sensitive contact info.
- **Concurrency on Sheets**: `gspread.append_row` is not transactional; concurrent submissions could in theory race on `_next_id`. Volume is expected to be low (survey responses), so this is acceptable today.
- **Schema drift**: deleting or renaming a question id silently orphans existing payload entries — they remain in `payload_json` but vanish from the section-wise view. Prefer additive changes.
- **Backups**: rely on the admin's manual CSV/XLSX download; no automated snapshot job.
