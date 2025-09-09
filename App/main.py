# App/main.py
import io
import pandas as pd
import streamlit as st
from pathlib import Path
from PIL import Image

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rail Currency",
    page_icon="🚆",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────────────
# Paths / assets
# ──────────────────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent

def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

DATA_PATH = first_existing([APP_DIR / "Rail.xlsx", ROOT_DIR / "Rail.xlsx"])
LOGO_PATH = first_existing([APP_DIR / "logo.png", ROOT_DIR / "logo.png"])

# ──────────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=True)
def load_data(path: Path) -> pd.DataFrame:
    if path is None:
        raise FileNotFoundError("Rail.xlsx not found in repo root or App/.")

    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.str.strip()

    required = {
        "Curr", "IO-Modul", "Denomination", "Emission",
        "Rail width", "Rail height", "Note width", "Note height",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing columns in Rail.xlsx: {sorted(missing)}")

    # normalize for stable filtering
    df["Curr"] = df["Curr"].astype(str).str.strip()
    df["IO-Modul"] = df["IO-Modul"].astype(str).str.strip()
    df["Emission"] = df["Emission"].astype(str).str.strip()
    df["Denomination_display"] = df["Denomination"].astype(str)

    # integers for KPI display
    for c in ["Rail width", "Rail height", "Note width", "Note height", "Rail width large"]:
        if c in df.columns:
            df[c] = df[c].astype("Int64")

    return df

def fmt_int(x):
    try:
        return int(x) if pd.notna(x) else "-"
    except Exception:
        return x

# ──────────────────────────────────────────────────────────────────────────────
# CSS (remove separators + keep clean cards/KPIs)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      :root{
        --bg:#F6F8FB; --card:#FFFFFF; --text:#0F2942; --muted:#6B7A90;
        --primary:#1FA2FF; --accent:#12D8FA; --accent2:#A6FFCB;
        --shadow:0 8px 24px rgba(15,41,66,.10); --radius:16px;
      }
      html, body, .block-container { background: var(--bg) !important; }

      /* Top bar */
      .topbar {
        display:flex; align-items:center; justify-content:space-between;
        background: var(--card); border-radius: 20px; padding: 12px 18px;
        box-shadow: var(--shadow); margin-bottom: 14px;
      }
      .brand { display:flex; align-items:center; gap:12px; }
      .btn-reset button { background:#EF4444; color:#fff; font-weight:700; border-radius:10px; }

      /* Cards */
      .filters-card, .specs-card, .table-card {
        background: var(--card); border-radius: var(--radius); padding: 18px;
        box-shadow: var(--shadow);
      }

      /* KPI cards */
      .kpi {
        background: var(--card);
        border-radius: 20px;
        padding: 18px 20px;
        text-align:center;
        box-shadow: var(--shadow);
        transition: transform .2s ease;
      }
      .kpi:hover { transform: translateY(-3px); }
      .kpi-title { color: var(--muted); font-size:.9rem; letter-spacing:.02em; }
      .kpi-value { color: var(--text); font-size:2.2rem; font-weight:800; line-height:1; }

      .chip {
        display:inline-flex; align-items:center; gap:8px; padding:6px 10px;
        background: var(--card); border-radius: 999px; border:1px solid rgba(0,0,0,.05);
        box-shadow: var(--shadow); margin-right:8px; margin-bottom:8px; color: var(--text);
        font-size: 0.9rem;
      }
      .center-title { text-align:center; margin: 10px 0 18px; color: var(--text); }

      /* ── REMOVE the white separators/lines Streamlit renders ───────────── */
      hr, div[role="separator"] { display:none !important; }
      /* Some Streamlit headings add a subtle bottom rule—hide it */
      .stHeading > div:has(h2) + hr { display:none !important; }
      /* Remove any accidental empty blocks that show as rounded bars */
      .block-container > div:empty { display:none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Top bar (bigger logo) + Reset on top-right
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="topbar">', unsafe_allow_html=True)
lcol, rcol = st.columns([0.75, 0.25], vertical_alignment="center")
with lcol:
    st.markdown('<div class="brand">', unsafe_allow_html=True)
    if LOGO_PATH:
        st.image(Image.open(LOGO_PATH), width=70)  # bigger DN icon
    st.markdown("</div>", unsafe_allow_html=True)
with rcol:
    st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Centered title
st.markdown("<h1 class='center-title'>Rail Currency</h1>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Load data
# ──────────────────────────────────────────────────────────────────────────────
try:
    df = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Filters (card) + chips — using st.query_params (no deprecation)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="filters-card">', unsafe_allow_html=True)
st.subheader("Select Parameters")  # no divider (no white rule)

qp = st.query_params

def pick_index(options, key):
    if not options:
        return 0
    v = qp.get(key, None)
    if v in options:
        return options.index(v)
    if isinstance(v, list) and v and v[0] in options:
        return options.index(v[0])
    return 0

# Step 1: Currency
currency_options = sorted(df["Curr"].dropna().unique().tolist())
sel_currency = st.selectbox("Step 1: Choose Currency", currency_options,
                            index=pick_index(currency_options, "curr"), key="sel_currency")
df_currency = df[df["Curr"] == sel_currency]

# Step 2: IO Module
io_options = sorted(df_currency["IO-Modul"].dropna().unique().tolist())
sel_io = st.selectbox("Step 2: Choose IO Module", io_options,
                      index=pick_index(io_options, "io"), key="sel_io")
df_io = df_currency[df_currency["IO-Modul"] == sel_io]

# Step 3: Denomination
denom_options = sorted(df_io["Denomination_display"].dropna().unique().tolist())
sel_denom = st.selectbox("Step 3: Choose Denomination", denom_options,
                         index=pick_index(denom_options, "denom"), key="sel_denom")
df_denom = df_io[df_io["Denomination_display"] == sel_denom]

# Step 4: Emission
emis_options = sorted(df_denom["Emission"].dropna().unique().tolist())
sel_emis = st.selectbox("Step 4: Choose Emission", emis_options,
                        index=pick_index(emis_options, "emis"), key="sel_emis")

# Update the shareable URL safely (no experimental API)
st.query_params.update({"curr": sel_currency, "io": sel_io, "denom": sel_denom, "emis": sel_emis})

# Active chips
st.markdown(
    f"""
    <div style='margin-top:8px;'>
      <span class="chip">Currency: <b>{sel_currency}</b></span>
      <span class="chip">IO: <b>{sel_io}</b></span>
      <span class="chip">Denom: <b>{sel_denom}</b></span>
      <span class="chip">Emission: <b>{sel_emis}</b></span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)  # end filters card

# Final filter
df_final = df_denom[df_denom["Emission"] == sel_emis]

# ──────────────────────────────────────────────────────────────────────────────
# KPI cards (results) — no extra white bars above
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="specs-card">', unsafe_allow_html=True)
st.subheader("Specifications")  # no divider

if df_final.empty:
    st.warning("No matching data found. Try another Emission or Denomination.")
else:
    row = df_final.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    for (title, value, col) in [
        ("RAIL WIDTH", row["Rail width"], c1),
        ("RAIL HEIGHT", row["Rail height"], c2),
        ("NOTE WIDTH", row["Note width"], c3),
        ("NOTE HEIGHT", row["Note height"], c4),
    ]:
        with col:
            st.markdown("<div class='kpi'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-title'>{title}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-value'>{fmt_int(value)}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    if "Rail width large" in df_final.columns and pd.notna(row.get("Rail width large", None)):
        st.caption(f"Rail width (large): {fmt_int(row['Rail width large'])}")

st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Results table + Excel export
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="table-card">', unsafe_allow_html=True)
st.subheader("Matching Row(s)")  # no divider

left_t, right_t = st.columns([0.5, 0.5])
with left_t:
    st.caption("Tip: Share the current URL to keep these selections.")
with right_t:
    if not df_final.empty:
        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "⬇️ Download Excel",
            data=buffer,
            file_name="rail_specs.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if df_final.empty:
    st.info("No rows to display for the current selection.")
else:
    cols = [
        "Curr", "Currency", "IO-Modul", "Denomination", "Emission",
        "Rail width", "Rail height", "Note width", "Note height",
    ]
    available = [c for c in cols if c in df_final.columns]
    st.dataframe(
        df_final[available].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────────
st.caption("v1.0 • Rail Currency Interface • © Your Team")
