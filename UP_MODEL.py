import streamlit as st
import numpy as np
import pickle
import datetime
import pathlib
import json
import logging
import os
from pathlib import Path

# Logging setup
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

log_filename = f"plant_tat_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
log_path = LOG_DIR / log_filename

# Create logger
logger = logging.getLogger("plant_tat_app")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers
if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s  |  %(levelname)-7s  |  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Quick shortcut functions
def log_info(msg):    logger.info(msg)
def log_warning(msg): logger.warning(msg)
def log_error(msg):   logger.error(msg)
def log_debug(msg):   logger.debug(msg)

############

# Streamlit page setup
st.set_page_config(
    page_title="Plant TAT Predictor",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Helper functions
def infer_shift_from_time(t: datetime.time) -> str:
    """Morning 06:00–13:59 | Afternoon 14:00–21:59 | Night 22:00–05:59"""
    h = t.hour
    if 6 <= h < 14:
        return "Morning Shift"
    elif 14 <= h < 22:
        return "Afternoon Shift"
    else:
        return "Night Shift"

def fmt_gate_in(dt_date: datetime.date, dt_time: datetime.time) -> str:
    dt = datetime.datetime.combine(dt_date, dt_time)
    return dt.strftime("%d/%m/%Y, %I:%M%p").lstrip("0").replace(" 0", " ")

def shift_icon(shift: str) -> str:
    return "☀️" if shift in ("Morning Shift", "Afternoon Shift") else "🌙"

def time_from_parts(hour12: int, minute: int, ampm: str) -> datetime.time:
    h = hour12 % 12
    if ampm.upper() == "PM":
        h += 12
    return datetime.time(h, minute, 0)

def parts_from_time(t: datetime.time):
    ampm = "AM" if t.hour < 12 else "PM"
    h12 = t.hour % 12
    if h12 == 0:
        h12 = 12
    return h12, t.minute, ampm

def sync_shift():
    st.session_state.shift = infer_shift_from_time(st.session_state.gate_time)

# Styling for Streamlit components
st.markdown(
    """
<style>

.stSelectbox > label {
            display: none !important;
        }
.stNumberInput > label {
            display: none !important;
        }
    /* App background */
    .stApp { background:#f5f7fb; }  /* Off-white background */

    /* Remove Streamlit chrome */
    header, [data-testid="stHeader"], [data-testid="stToolbar"], div[data-testid="stDecoration"] { display:none !important; }

    /* Pull everything up + compact page */
    [data-testid="stAppViewContainer"] > .main { padding-top: 0rem !important; }
    .block-container{
        padding-top: 0rem !important;
        padding-bottom: 1.0rem !important;
        margin-top: 0rem !important;
        max-width: 980px !important;
    }

    /* Header */
    .autoplant-brand{
        text-align:center; font-weight:900; color:#dc2626; font-size:3rem;
        margin: 0.02rem 0 0.0rem; letter-spacing:-0.5px;
    }
    .main-title{
        text-align:center; font-weight:900; color:#111827; font-size:3rem;
        margin: 0.0rem 0 0.05rem;
    }
    .subtitle{
        text-align:center; color:#6b7280; font-size:1.2rem;
        margin: 0.0rem 0 0.65rem;
    }

    /* Card container */
    div[data-testid="stContainer"]{
        background:#fff !important;
        border:1px solid #e6eaf0 !important;
        border-radius:16px !important;
        padding:1.0rem 1.2rem 0.9rem !important;
        box-shadow:0 10px 26px rgba(17,24,39,0.08) !important;
    }
    /* Labels */
    .field-label{
        color:#6b7280;
        font-weight:normal;
        font-size:1.3rem !important; /* Set font size to 1.3rem */
        margin: 0.10rem 0 0.25rem;
    }
    label, .stSelectbox label, .stNumberInput label, .stDateInput label, .stTimeInput label{
        color:#6b7280 !important;
        font-weight:normal !important;
        font-size:1.3rem !important; /* Set font size to 1.3rem for all labels */
    }
    /* Inputs base */
   
    .stSelectbox > div > div,
    .stDateInput > div > div{
        background:#fff !important;
        border:1px solid #dfe5ee !important;
        border-radius:12px !important;
        min-height:50px !important;
    }

    /* Increase font size for Plant Code, Material Code, Seq Packer, Qty, and PackType */
    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stNumberInput"] > div > div {
        font-size: 1.5rem !important; /* Set font size to 1.5rem for all input fields */
    }
    div[data-testid="stNumberInput"] input {
        font-size: 1.4rem !important; /* Adjust for number input fields like Qty */
    }
    
    /* Select values (Hour/Minute/AMPM) */
    div[data-baseweb="select"] *{
        color:#111827 !important;

        -webkit-text-fill-color:#111827 !important;
        opacity:2 !important;
        font-weight:normal !important;
        font-size:1.3rem !important; /* Adjust font size for select values */
    }

    /* Date input text black */
    div[data-testid="stDateInput"] input{
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
        opacity:1 !important;
        background:#ffffff !important;
        font-size:1.3rem !important; /* Increase font size for date input */
    }

    /* Number input */
    div[data-testid="stNumberInput"] > div{
        background:#ffffff !important;
        border:1px solid #dfe5ee !important;
        border-radius:12px !important;
    }
    div[data-testid="stNumberInput"] input{
        background:#ffffff !important;
        color:#111827 !important;
        -webkit-text-fill-color:#111827 !important;
        font-weight:normal !important;
        font-size:1.3rem !important; /* Adjust number input font size */
    }
    div[data-testid="stNumberInput"] button{
        background:#ffffff !important;
        color:#111827 !important;
        border-left:1px solid #dfe5ee !important;
        font-size:1.3rem !important;
    }
    div[data-testid="stNumberInput"] button:hover{
        background:#f9fafb !important;
    }

    /* Gate-in row (main form) */
    .gatein-row{
        display:flex;
        align-items:center;
        gap:12px;
        background:#ffffff;
        border:1px solid #dfe5ee;
        border-radius:12px;
        min-height:50px;
        padding:0 14px;
        width:100%;
    }
    .gatein-text{
        flex: 1 1 auto;
        min-width: 0;
        color:#111827;
        font-weight:normal;
        font-size:1.2rem !important; /* Increase font size for gate-in text */
    }
    .shift-pill{
        flex: 0 0 auto;
        display:flex;
        align-items:center;
        gap:6px;
        padding:5px 12px;
        border-radius:999px;
        border:1px solid #e5e7eb;
        background:#fff;
        font-weight:normal;
        color:#111827;
        font-size:1.3rem !important; /* Increase font size for shift pills */
    }

    

/* Calendar popup container */
div[data-baseweb="popover"]{
    background:#f8fafc !important;   /* off-white */
    color:white !important;
    border-radius:12px !important;
    border:1px solid #e5e7eb !important;
}

/* Calendar header (month/year bar) */
div[data-baseweb="calendar"] header{
    background:#ffffff !important;
    color:white !important;
}

/* Weekday labels */
div[data-baseweb="calendar"] th{
    color:#6b7280 !important;
    font-weight:500;
}

/* Calendar days */
div[data-baseweb="calendar"] td{
    color:#111827 !important;
}

/* Selected day */
div[data-baseweb="calendar"] [aria-selected="true"]{
    background:#ef4444 !important;  /* red highlight */
    color:white !important;
    border-radius:50% !important;
}

/* Hover day */
div[data-baseweb="calendar"] td:hover{
    background:#e5e7eb !important;
    border-radius:8px;
}


    /* Calendar icon */
    button[data-testid="stPopoverButton"]{
        background:#ffffff !important;
        border:1px solid #dfe5ee !important;
        color:#111827 !important;
        border-radius:12px !important;
        height:50px !important;
        padding:0 15px !important;
        font-weight:normal !important;
        font-size:1.3rem !important;
        width: 100% !important;
        transition: transform .12s ease, box-shadow .12s ease;
    }
    button[data-testid="stPopoverButton"]:hover{
        background:#ffffff !important;
        border-color:#ffffff !important;
        transform: translateY(-1px);
        box-shadow:0 10px 16px rgba(17,24,39,0.10) !important;
    }

    /* Shift bars (compact stacked layout) */
    .shiftbar {
        margin-bottom: 8px !important;
    }

    .shiftbar button{
        height:50px !important;
        border-radius:14px !important;
        font-weight:normal !important;
        padding:0.5rem 1.0rem !important;
        width:100% !important;
        white-space:nowrap !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
        font-size:1.3rem !important;
        transition: transform .12s ease, box-shadow .12s ease;
    }
    .shiftbar button:hover{
        transform: translateY(-1px);
        box-shadow: 0 10px 18px rgba(17,24,39,0.15);
    }

    /* Shift colors */
    .shiftbar-morning button{
        background:#f59e0b !important;
        color:#ffffff !important;
        border:1px solid #f59e0b !important;
    }
    .shiftbar-afternoon button{
        background:#fef3c7 !important;
        color:#92400e !important;
        border:1px solid #fde68a !important;
    }
    .shiftbar-night button{
        background:#e5e7eb !important;
        color:#111827 !important;
        border:1px solid #d1d5db !important;
    }
    .shiftbar-active button{
        box-shadow: 0 16px 26px rgba(17,24,39,0.18) !important;
        outline: 2px solid rgba(59,130,246,0.30) !important;
    }

    /* Predict button */
    div.stButton > button{
        background:#6F9CDE !important;
        color:#fff !important;
        font-weight:normal !important;
        font-size: 1.3rem !important;
        border-radius:12px !important;
        padding:0.85rem 1.0rem !important;
        width:100% !important;
        border:none !important;
        box-shadow:0 10px 18px rgba(43,91,215,0.22) !important;
        margin-top:0.60rem !important;
        transition: transform .12s ease, box-shadow .12s ease;
    }
    div.stButton > button:hover{
        background:#1f4fbf !important;
        transform: translateY(-1px);
        box-shadow:0 14px 22px rgba(43,91,215,0.26) !important;
    }
    div.stButton > button::before{ content:" "; margin-right:0.55rem; }

    /* Result cards */
    .result-wrap{ margin-top:0.9rem; margin-bottom:0.2rem; }
    .result-card{
        background:#ffffff; border:1px solid #eef2f7; border-radius:12px;
        box-shadow:0 10px 20px rgba(17,24,39,0.08);
        overflow:hidden; width:100%;
    }
    .result-head{
        padding:10px 14px; font-weight:normal; font-size:1.2rem; color:#ffffff;
        display:flex; align-items:center; justify-content:center; gap:8px;
    }
    .head-amber{ background:#d6b270; }
    .head-gossamer{ background:#009688 !important; }  /* Dark gossamer color */
    .result-body{ padding:12px 14px 14px; text-align:center; }
    .result-big{ font-weight:normal; font-size:2.5rem; color:#111827; line-height:1.1; margin-top:2px; }
    .result-sub{ margin-top:6px; color:#6b7280; font-weight:normal; font-size:1rem; }
</style>
""", unsafe_allow_html=True)

# Model and Data loading functions
BASE_DIR = pathlib.Path(__file__).parent

@st.cache_resource(show_spinner=False)
def load_model():
    with open(BASE_DIR / "xgboost_model_t.pkl", "rb") as f:
        return pickle.load(f)

@st.cache_resource(show_spinner=False)
def load_dictionary():
    with open(BASE_DIR / "dictionary_xgb_t.json", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_resource(show_spinner=False)
def load_label_maps():
    with open(BASE_DIR / "label_maps_xgb_t.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Load the model and data
try:
    model = load_model()
    dictionary = load_dictionary()
    label_maps = load_label_maps()
    log_info("Model, dictionary, and label maps loaded successfully")
except Exception as e:
    log_error(f"Failed to load model/data: {e}")
    st.error(f"Failed to load required model/data: {e}")
    st.stop()

def plant_list(key, plant):
    scope = dictionary.get(key, {})
    if isinstance(scope, dict):
        return list(scope.get(plant, []))
    if isinstance(scope, list):
        return scope
    return []

# App header and inputs
st.markdown('<div class="autoplant-brand">autoplant</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">Plant TAT Predictor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Estimate truck loading and gate-out time at plant entry</div>', unsafe_allow_html=True)

# Session State Initialization
if "gate_date" not in st.session_state:
    st.session_state.gate_date = datetime.date.today()

if "gate_time" not in st.session_state:
    now = datetime.datetime.now()
    st.session_state.gate_time = datetime.time(now.hour, now.minute, 0)

if "shift" not in st.session_state:
    st.session_state.shift = infer_shift_from_time(st.session_state.gate_time)

if "pred_min" not in st.session_state:
    st.session_state.pred_min = None
if "gate_out_str" not in st.session_state:
    st.session_state.gate_out_str = None

sync_shift()

# Form Layout
with st.container(border=True):
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="field-label">Plant Code</div>', unsafe_allow_html=True)
        plant_options = sorted(dictionary.get("PLANT_CODE", []))
        plant = st.selectbox("", plant_options, key="plant_code")

        st.markdown('<div class="field-label">Gate-In Date &amp; Time</div>', unsafe_allow_html=True)

        gate_text = fmt_gate_in(st.session_state.gate_date, st.session_state.gate_time)
        shift_txt = st.session_state.shift
        ico = shift_icon(shift_txt)


        g1, g2 = st.columns([0.80, 0.20], gap="small")
        with g1:
            st.markdown(
                f"""
<div class="gatein-row">
  <div class="gatein-text">{gate_text}</div>
  <div class="shift-pill">{ico} {shift_txt}</div>
</div>
""",
                unsafe_allow_html=True
            )

        # Popover: layout
        with g2:
            with st.popover("📅", use_container_width=True):
                left, right = st.columns([1.25, 2.00], gap="large")

                with left:
                    st.markdown('<div class="field-label">Gate-In Date</div>', unsafe_allow_html=True)
                    st.session_state.gate_date = st.date_input(
                        "",
                        st.session_state.gate_date,
                        key="gate_date_pop"
                    )

                with right:
                    st.markdown('<div class="field-label">Enter Time</div>', unsafe_allow_html=True)

                    h12, mm, ap = parts_from_time(st.session_state.gate_time)

                    t1, t2, t3 = st.columns([1.07, 1.09, 0.92], gap="small")
                    with t1:
                        st.markdown('<div class="bigtime">', unsafe_allow_html=True)
                        hour12 = st.selectbox("Hour", list(range(1, 13)),
                                              index=list(range(1, 13)).index(h12),
                                              key="hour12_pop")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with t2:
                        st.markdown('<div class="bigtime">', unsafe_allow_html=True)
                        minute = st.selectbox("Minute", list(range(0, 60)),
                                              index=list(range(0, 60)).index(mm),
                                              key="minute_pop")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with t3:
                        st.markdown('<div class="ampm">', unsafe_allow_html=True)
                        ampm = st.selectbox("AM/PM", ["AM", "PM"],
                                            index=["AM", "PM"].index(ap),
                                            key="ampm_pop")
                        st.markdown('</div>', unsafe_allow_html=True)

                    st.session_state.gate_time = time_from_parts(hour12, minute, ampm)
                    sync_shift()

                    st.markdown('<div class="field-label" style="margin-top:10px;">Shift</div>', unsafe_allow_html=True)

                    def set_shift_start(target):
                        m = st.session_state.gate_time.minute
                        if target == "Morning Shift":
                            st.session_state.gate_time = datetime.time(6, m, 0)
                        elif target == "Afternoon Shift":
                            st.session_state.gate_time = datetime.time(14, m, 0)
                        else:
                            st.session_state.gate_time = datetime.time(22, m, 0)
                        sync_shift()

                    cur = st.session_state.shift

                    # Active outline class
                    m_active = " shiftbar-active" if cur == "Morning Shift" else ""
                    a_active = " shiftbar-active" if cur == "Afternoon Shift" else ""
                    n_active = " shiftbar-active" if cur == "Night Shift" else ""

                    st.markdown(f'<div class="shiftbar shiftbar-morning{m_active}">', unsafe_allow_html=True)
                    if st.button("☀️  Morning   (6AM–2PM)", use_container_width=True, key="btn_morning"):
                        set_shift_start("Morning Shift")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown(f'<div class="shiftbar shiftbar-afternoon{a_active}">', unsafe_allow_html=True)
                    if st.button("🌤️  Afternoon  (2PM–10PM)", use_container_width=True, key="btn_afternoon"):
                        set_shift_start("Afternoon Shift")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown(f'<div class="shiftbar shiftbar-night{n_active}">', unsafe_allow_html=True)
                    if st.button("🌙  Night  (10PM–6AM)", use_container_width=True, key="btn_night"):
                        set_shift_start("Night Shift")
                    st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="field-label">SEQ_PACKER</div>', unsafe_allow_html=True)

        packer_options = sorted(plant_list("SEQ_PACKER", plant))
        packer = st.selectbox("", packer_options or ["Select packer"], key="seq_packer")

    with col2:
        st.markdown('<div class="field-label">Material Code</div>', unsafe_allow_html=True)

        material_options = sorted(plant_list("MATERIAL_CODE", plant))
        material = st.selectbox("", material_options or ["Select material"], key="material_code")

        st.markdown('<div class="field-label">Pack Type</div>', unsafe_allow_html=True)

        pack_options = plant_list("PACK", plant)
        pack = st.selectbox("", pack_options or ["Select pack type"], key="pack_type")

        st.markdown('<div class="field-label">Total Qty</div>', unsafe_allow_html=True)

        qty = st.number_input("", min_value=0.0, value=20.0, step=1.0, key="qty")

    predict = st.button("⏳ Predict Plant TAT", use_container_width=True)

if predict:
    try:
        sync_shift()

        plant_idx = label_maps.get("PLANT_CODE", {}).get(plant, 0)
        seq_idx   = label_maps.get("SEQ_PACKER", {}).get(packer, 0)
        mat_idx   = label_maps.get("MATERIAL_CODE", {}).get(material, 0)
        shift_idx = label_maps.get("Shift", {}).get(st.session_state.shift, 0)
        pack_idx  = label_maps.get("PACK", {}).get(pack, 0)

        gatein_dt = datetime.datetime.combine(st.session_state.gate_date, st.session_state.gate_time)

        features = [
            seq_idx, mat_idx, shift_idx, plant_idx, pack_idx,
            float(qty), gatein_dt.month, gatein_dt.hour, gatein_dt.day, gatein_dt.year
        ]
        X = np.array(features, dtype=float).reshape(1, -1)

        pred_min = max(0, int(round(float(model.predict(X)[0]))))
        gate_out = gatein_dt + datetime.timedelta(minutes=pred_min)
        gate_out_str = gate_out.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")
        ### log
        log_info(f"Prediction made | Plant={plant} | Packer={packer} | "
                 f"Material={material} | Pack={pack} | Qty={qty} | "
                 f"Shift={st.session_state.shift} | "
                 f"Gate-in={gate_text} → Est. {pred_min} min → Out {gate_out_str}")
        ###
        st.session_state.pred_min = pred_min
        st.session_state.gate_out_str = gate_out_str

    except Exception as e:

        ##logger for error
        log_error(f"Prediction failed: {str(e)}")
        ##############
        st.error(f"Prediction failed: {e}")

if st.session_state.pred_min is not None and st.session_state.gate_out_str is not None:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(
            f"""
<div class="result-wrap">
  <div class="result-card">
    <div class="result-head head-amber">Estimated Loading Time ⏱️</div>
    <div class="result-body">
      <div class="result-big">~{st.session_state.pred_min} Minutes</div>
      <div class="result-sub">Based on current queue &amp; conditions</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
<div class="result-wrap">
  <div class="result-card">
    <div class="result-head head-gossamer">Estimated Gate-Out 🚚</div>
    <div class="result-body">
      <div class="result-big">{st.session_state.gate_out_str}</div>
      <div class="result-sub">± 10 Min accuracy</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True
        )
