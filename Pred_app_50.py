# app.py
import json
import pickle
import pandas as pd
import streamlit as st
import numpy as np

#  PAGE CONFIG 
st.set_page_config(
    page_title="Loading Time Predictor",
    layout="centered",
    initial_sidebar_state="expanded"
)
st.title("⏱️ Loading Time Predictor")
st.markdown("### Predict **GateOut – GateIn time (in minutes)** for every hour of the day")

# LOAD MODEL & MAPS 
@st.cache_resource
def load_model_and_maps():
    try:
        with open("xgboost_model_Hour.pkl", "rb") as f:
            model = pickle.load(f)
        with open("label_maps_xgb_Hour.json", "r", encoding="utf-8") as f:
            label_maps = json.load(f)
        return model, label_maps
    except FileNotFoundError as e:
        st.error(f"File not found: {e}. Make sure both files are in the same folder.")
        st.stop()
    except Exception as e:
        st.error(f"Error loading model/maps: {e}")
        st.stop()

model, label_maps = load_model_and_maps()

# CONSTANTS
CAT_COLS = ['MATERIAL_CODE', 'PLANT_CODE', 'PACK', 'Hour_Group']
NUM_COLS = ['TOTAL_QTY', 'Month', 'Day', 'Year']

# Extract valid categorical values
VALID_VALUES = {}
for col in CAT_COLS:
    vals = [k for k in label_maps[col].keys() if str(k).lower() not in ['nan', '']]
    VALID_VALUES[col] = sorted(vals)

#  ENCODING FUNCTION 
def encode_input(data: dict):
    row = []
    for col in CAT_COLS:
        val = str(data.get(col, ""))
        code = label_maps[col].get(val, 0)
        row.append(code)
    for col in NUM_COLS:
        row.append(float(data.get(col, 0)))
    return np.array([row], dtype=np.float32)

# SIDEBAR INPUTS 
st.sidebar.header("🚚 Input Parameters")

plant = st.sidebar.selectbox("Plant Code", options=VALID_VALUES.get("PLANT_CODE", ["AC01"]))
material = st.sidebar.selectbox("Material", options=VALID_VALUES.get("MATERIAL_CODE", ["CLINKER"]))
pack = st.sidebar.selectbox("Pack Type", options=VALID_VALUES.get("PACK", ["Bag", "Cli", "Loose"]))

qty = st.sidebar.number_input("Total Quantity (tons)", min_value=0.1, value=40.0, step=1.0)

col1, col2, col3 = st.sidebar.columns(3)
month = col1.number_input("Month", 1, 12, 1)
day = col2.number_input("Day", 1, 31, 20)
year = col3.number_input("Year", 2024, 2030, 2025)

# PREDICTION
if st.sidebar.button("🔮 Predict Loading Time for All Hours", type="primary", use_container_width=True):

    base_input = {
        "MATERIAL_CODE": material,
        "PLANT_CODE": plant,
        "PACK": pack,
        "TOTAL_QTY": qty,
        "Month": month,
        "Day": day,
        "Year": year
    }

    hour_groups = VALID_VALUES.get("Hour_Group", [])
    
    # Sort hours properly: 0-1 → 23-0
    def hour_sort_key(h):
        try:
            return int(h.split('-')[0])
        except:
            return 999
    hour_groups_sorted = sorted(hour_groups, key=hour_sort_key)

    results = []
    for hg in hour_groups_sorted:
        input_data = base_input.copy()
        input_data["Hour_Group"] = hg
        X = encode_input(input_data)
        pred_hours = float(model.predict(X)[0])
        
        # CORRECT: Convert hours → minutes
        pred_minutes = max(0, int(round(pred_hours)))
        
        results.append({"Hour_Group": hg, "Predicted_Time_Minutes": pred_minutes})

    df = pd.DataFrame(results)

    # Find best (fastest) hour
    best_row = df.loc[df["Predicted_Time_Minutes"].idxmin()]
    best_hour = best_row["Hour_Group"]
    best_time = best_row["Predicted_Time_Minutes"]

    # DISPLAY RESULTS 
    st.success(" Prediction completed for all hour")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Time", f"{df['Predicted_Time_Minutes'].mean():.0f} min")
    with col2:
        st.metric("Worst (Peak) Hour", f"{df['Predicted_Time_Minutes'].max()} min")

    # Color styling function (no matplotlib needed!)
    def highlight_time(val):
        if val <= 30:
            color = "#d4edda"   # Green
        elif val <= 60:
            color = "#fff3cd"   # Yellow
        elif val <= 90:
            color = "#f8d7da"   # Light Red
        else:
            color = "#f5c6cb"   # Red
        bold = "bold" if val == best_time else "normal"
        return f'background-color: {color}; color: black; font-weight: {bold}; text-align: center; padding: 10px;'

    styled_df = df.style\
        .applymap(highlight_time, subset=["Predicted_Time_Minutes"])\
        .format({"Predicted_Time_Minutes": "{:.0f} min"})\
        .set_properties(**{"font-size": "16px"}, subset=["Hour_Group"])

    st.subheader("Predicted Loading Time by Hour")
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Line chart
    st.subheader("Daily Trend")
    st.line_chart(df.set_index("Hour_Group")["Predicted_Time_Minutes"], use_container_width=True)

    # Download
    csv = df.to_csv(index=False).encode()
    st.download_button(
        " Download as CSV",
        data=csv,
        file_name=f"Loading_Time_{plant}_{material}_{int(qty)}t_{year}{month:02d}{day:02d}.csv",
        mime="text/csv",
        use_container_width=True
    )
# INFO EXPANDER 
with st.expander(" Model Info"):
    st.write("**Model predicts time in hours → converted to minutes**")
    st.write("**Green** = Fast (<30 min) | **Yellow** = Normal | **Red** = Slow (>90 min)")
    st.caption("Best hour is highlighted in bold")