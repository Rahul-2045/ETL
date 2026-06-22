from flask import Flask, render_template, request, jsonify
import numpy as np
import pickle
import json
import datetime
import pathlib

app = Flask(__name__)

BASE_DIR = pathlib.Path(__file__).parent

# ---------- Load model/data once ----------
def load_pickle(path: str):
    with open(BASE_DIR / path, "rb") as f:
        return pickle.load(f)

def load_json(path: str):
    with open(BASE_DIR / path, "r", encoding="utf-8") as f:
        return json.load(f)

try:
    model = load_pickle("xgboost_model_t.pkl")
    dictionary = load_json("dictionary_xgb_t.json")
    label_maps = load_json("label_maps_xgb_t.json")
except Exception as e:
    raise RuntimeError(f"Failed to load required model/data files: {e}")

# ---------- Helpers ----------
def plant_list(key, plant):
    scope = dictionary.get(key, {})
    if isinstance(scope, dict):
        return list(scope.get(plant, []))
    if isinstance(scope, list):
        return scope
    return []

def safe_get_label(map_key: str, value: str) -> int:
    # returns 0 if not found
    return int(label_maps.get(map_key, {}).get(value, 0))

def safe_first(lst):
    return lst[0] if lst else ""


# ---------- API for dependent dropdowns ----------
@app.get("/api/options")
def api_options():
    plant = request.args.get("plant", "")
    return jsonify({
        "SEQ_PACKER": sorted(plant_list("SEQ_PACKER", plant)),
        "MATERIAL_CODE": sorted(plant_list("MATERIAL_CODE", plant)),
        "Shift": sorted(plant_list("Shift", plant)),
        "PACK": sorted(plant_list("PACK", plant)),
    })


# ---------- Main page ----------
@app.route("/", methods=["GET", "POST"])
def index():
    plant_options = sorted(dictionary.get("PLANT_CODE", []))
    selected_plant = plant_options[0] if plant_options else ""

    # Default date/time
    today = datetime.date.today()
    now = datetime.datetime.now()
    default_date = today.isoformat()
    default_time = f"{now.hour:02d}:00"

    # Load options for the selected plant
    packer_options = sorted(plant_list("SEQ_PACKER", selected_plant))
    material_options = sorted(plant_list("MATERIAL_CODE", selected_plant))
    shift_options = sorted(plant_list("Shift", selected_plant))
    pack_options = sorted(plant_list("PACK", selected_plant))

    # Default selected values
    selected_packer = safe_first(packer_options)
    selected_material = safe_first(material_options)
    selected_shift = safe_first(shift_options)
    selected_pack = safe_first(pack_options)
    total_qty = 100.0
    gatein_date = default_date
    gatein_time = default_time

    result = None
    error = None

    if request.method == "POST":
        try:
            selected_plant = request.form.get("PLANT_CODE", selected_plant)

            # refresh options after plant selection (important)
            packer_options = sorted(plant_list("SEQ_PACKER", selected_plant))
            material_options = sorted(plant_list("MATERIAL_CODE", selected_plant))
            shift_options = sorted(plant_list("Shift", selected_plant))
            pack_options = sorted(plant_list("PACK", selected_plant))

            # read submitted values
            selected_packer = request.form.get("SEQ_PACKER", safe_first(packer_options))
            selected_material = request.form.get("MATERIAL_CODE", safe_first(material_options))
            selected_shift = request.form.get("Shift", safe_first(shift_options))
            selected_pack = request.form.get("PACK", safe_first(pack_options))

            gatein_date = request.form.get("GateInDate", default_date)
            gatein_time = request.form.get("GateInTime", default_time)
            total_qty = float(request.form.get("TOTAL_QTY", "100") or 100)

            # Encode
            plant_idx = safe_get_label("PLANT_CODE", selected_plant)
            seq_idx = safe_get_label("SEQ_PACKER", selected_packer)
            mat_idx = safe_get_label("MATERIAL_CODE", selected_material)
            shift_idx = safe_get_label("Shift", selected_shift)
            pack_idx = safe_get_label("PACK", selected_pack)

            # Date/time parts
            d = datetime.date.fromisoformat(gatein_date)
            t = datetime.time.fromisoformat(gatein_time)

            input_row = [
                seq_idx,
                mat_idx,
                shift_idx,
                plant_idx,
                pack_idx,
                float(total_qty),
                d.month,
                t.hour,
                d.day,
                d.year,
            ]

            x = np.array(input_row, dtype=float).reshape(1, -1)
            pred = float(model.predict(x)[0])
            pred = max(pred, 0.0)

            gatein_dt = datetime.datetime.combine(d, t)
            gateout_dt = gatein_dt + datetime.timedelta(minutes=round(pred))

            result = {
                "pred_minutes": int(round(pred)),
                "gateout_time": gateout_dt.strftime("%H:%M"),
            }

        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        plant_options=plant_options,
        packer_options=packer_options,
        material_options=material_options,
        shift_options=shift_options,
        pack_options=pack_options,
        selected_plant=selected_plant,
        selected_packer=selected_packer,
        selected_material=selected_material,
        selected_shift=selected_shift,
        selected_pack=selected_pack,
        total_qty=total_qty,
        gatein_date=gatein_date,
        gatein_time=gatein_time,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    # IMPORTANT for your error: disable reloader
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
