# App/main.py
import pandas as pd
import streamlit as st
from PIL import Image
from pathlib import Path

# =========================
# Page config (creative)
# =========================
st.set_page_config(
    page_title="Rail Currency Interface",
    page_icon="🚆",   # change to your favicon or keep the emoji
    layout="wide"
)

# =========================
# Paths (robust for Cloud)
# =========================
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

# =========================
# Header / Branding
# =========================
if LOGO_PATH:
    try:
        st.image(Image.open(LOGO_PATH), width=160)
    except Exception as e:
        st.warning(f"Logo could not be loaded: {e}")

st.markdown(
    "<h1 style='text-align:center;margin-top:-10px;color:#0f2942;'>"
    "Automated Rail Currency Interface</h1>",
    unsafe_allow_html=True,
)

# =========================
# Light styling
# =========================
st.markdown(
    """
    <style>
      .main { background-color: #f6f8fb; }
      h1, h2, h3 { color: #0f2942; }
      .stSelectbox label { font-weight: 700; color: #0f2942; }
      .specs-card {
          background: white;
          border-radius: 14px;
          padding: 16px 18px;
          box-shadow: 0 3px 12px rgba(0,0,0,0.08);
          margin-top: 10px;
      }
      .reset-btn button {
          background-color: #ff4b4b !important;
          color: white !important;
          font-weight: 700;
          border-radius: 10px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Data loading
# =========================
@st.cache_data(show_spinner=True)
def load_data(path: Path) -> pd.DataFrame:
    if path is None:
        raise FileNotFoundError("Rail.xlsx not found. Put it in the repo root or in App/.")

    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.str.strip()

    # Validate required columns
    required = {
        "Curr", "IO-Modul", "Denomination", "Emission",
        "Rail width", "Rail height", "Note width", "Note height"
    }
    missing = required.difference(set(df.columns))
    if missing:
        raise ValueError(f"Missing columns in Rail.xlsx: {sorted(missing)}")

    # Normalize for filtering (strings)
    df["Curr"] = df["Curr"].astype(str).str.strip()
    df["IO-Modul"] = df["IO-Modul"].astype(str).str.strip()
    df["Emission"] = df["Emission"].astype(str).str.strip()
    df["Denomination_display"] = df["Denomination"].astype(str)

    # Cast numeric display columns to integer (nullable) to avoid "3.0"
    int_cols = ["Rail width", "Rail height", "Note width", "Note height", "Rail width large"]
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    return df

try:
    df = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# =========================
# Reset button (top-right)
# =========================
left, right = st.columns([0.75, 0.25])
with right:
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("🔄 Reset"):
        st.session_state.clear()
        st.experimental_set_query_params()  # clear any URL params if you add them later
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Controls
# =========================
st.subheader("Select Parameters")

# Step 1: Currency
currency_options = sorted(df["Curr"].dropna().unique().tolist())
selected_currency = st.selectbox("Step 1: Choose Currency", currency_options)

df_currency = df[df["Curr"] == selected_currency]

# Step 2: IO Module
io_module_options = sorted(df_currency["IO-Modul"].dropna().unique().tolist())
selected_io_module = st.selectbox("Step 2: Choose IO Module", io_module_options)

df_io = df_currency[df_currency["IO-Modul"] == selected_io_module]

# Step 3: Denomination
denomination_options = sorted(df_io["Denomination_display"].dropna().unique().tolist())
selected_denomination_display = st.selectbox("Step 3: Choose Denomination", denomination_options)

df_denom = df_io[df_io["Denomination_display"] == selected_denomination_display]

# Step 4: Emission
emission_options = sorted(df_denom["Emission"].dropna().unique().tolist())
selected_emission = st.selectbox("Step 4: Choose Emission", emission_options)

df_final = df_denom[df_denom["Emission"] == selected_emission]

# =========================
# Results
# =========================
st.subheader("Final Specifications")
if df_final.empty:
    st.warning("No matching data found for the selected combination.")
else:
    specs = df_final.iloc[0]

    # specs card with metrics
    st.markdown('<div class="specs-card">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    # Use int() to ensure display has no .0 even if dtype changes later
    def fmt_int(x):
        try:
            return int(x) if pd.notna(x) else "-"
        except Exception:
            return x

    c1.metric("Rail Width", f"{fmt_int(specs['Rail width'])}")
    c2.metric("Rail Height", f"{fmt_int(specs['Rail height'])}")
    c3.metric("Note Width", f"{fmt_int(specs['Note width'])}")
    c4.metric("Note Height", f"{fmt_int(specs['Note height'])}")
    st.markdown("</div>", unsafe_allow_html=True)

    if "Rail width large" in df_final.columns and pd.notna(specs.get("Rail width large", None)):
        st.caption(f"Rail width (large): {fmt_int(specs['Rail width large'])}")

    with st.expander("Show matching row(s)"):
        cols = [
            "Curr", "Currency", "IO-Modul", "Denomination", "Emission",
            "Rail width", "Rail height", "Note width", "Note height"
        ]
        available = [c for c in cols if c in df_final.columns]
        st.dataframe(df_final[available].reset_index(drop=True), use_container_width=True)

with st.expander("How this works"):
    st.write(
        "Choose Currency → IO Module → Denomination → Emission. "
        "The first matching row is summarized above; open the table to see all matches."
    )
