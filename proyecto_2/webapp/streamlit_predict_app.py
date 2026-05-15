import os
import json
import requests
import streamlit as st

# --- Configuración de la API ---
# Se utiliza el valor por defecto si la variable de entorno no existe
DEFAULT_API = "http://localhost:8000/predict"
API_URL = (os.getenv("PREDICT_API_URL") or "http://localhost:8000") + "/predict"

def _none_if_empty(s: str):
    if s is None:
        return None
    s = str(s).strip()
    return None if s == "" else s

def _int_or_none(v):
    try:
        if v is None or str(v).strip() == "":
            return None
        return int(v)
    except Exception:
        return None

def _float_or_zero(v):
    try:
        if v is None or str(v).strip() == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0

def predict_request(payload):
    status = f"POST {API_URL}"
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        status += f"\nStatus: {resp.status_code}"
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        pretty = None
        if isinstance(data, dict):
            for key in ("prediction", "pred", "class", "label", "result", "readmitted"):
                if key in data:
                    pretty = f"**Model output ({key})**: {data[key]}"
                    break
        if pretty is None:
            pretty = "**Model output**: (see JSON below)"

        return data, pretty, status

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, "**Request failed** — check API_URL and server logs.", status

# --- Constantes de la Interfaz ---
MED_DIRS = ["No", "Steady", "Up", "Down"]
AGE_BUCKETS = ["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)", "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"]
RACES = ["Caucasian", "AfricanAmerican", "Asian", "Hispanic", "Other", "?"]
GENDERS = ["Male", "Female", "Unknown/Invalid", "?"]

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="Diabetes Readmission", layout="wide")

st.title("🩺 Diabetes Readmission — via `/predict`")
st.markdown(f"""
Fill the fields and click **Predict**.  
This app will POST the JSON body to your API and display the response.

> Endpoint: `{API_URL}`
""")

# Dividimos la pantalla en dos columnas principales
col_input, col_output = st.columns([2, 1])

with col_input:
    st.subheader("Patient & Encounter")
    c1, c2 = st.columns(2)
    with c1:
        encounter_id = st.number_input("encounter_id", value=39877476, step=1)
        patient_nbr = st.number_input("patient_nbr", value=4226301, step=1)
        race = st.selectbox("race", options=RACES, index=0)
    with c2:
        gender = st.selectbox("gender", options=GENDERS, index=0)
        age = st.selectbox("age", options=AGE_BUCKETS, index=5)
        weight = st.text_input("weight (blank = null)", value="")

    st.subheader("Admission / Discharge")
    c3, c4 = st.columns(2)
    with c3:
        admission_type_id = st.number_input("admission_type_id", value=1, step=1)
        discharge_disposition_id = st.number_input("discharge_disposition_id", value=1, step=1)
        admission_source_id = st.number_input("admission_source_id", value=7, step=1)
    with c4:
        time_in_hospital = st.number_input("time_in_hospital", value=2, step=1)
        payer_code = st.text_input("payer_code (blank = null)", value="")
        medical_specialty = st.text_input("medical_specialty", value="Family/GeneralPractice")

    st.subheader("Procedure / Meds Counts")
    c5, c6 = st.columns(2)
    with c5:
        num_lab_procedures = st.number_input("num_lab_procedures", value=35, step=1)
        num_procedures = st.number_input("num_procedures", value=0, step=1)
        num_medications = st.number_input("num_medications", value=7, step=1)
    with c6:
        number_outpatient = st.number_input("number_outpatient", value=0, step=1)
        number_emergency = st.number_input("number_emergency", value=0, step=1)
        number_inpatient = st.number_input("number_inpatient", value=0, step=1)

    st.subheader("Diagnoses & Labs")
    c7, c8 = st.columns(2)
    with c7:
        diag_1 = st.text_input("diag_1", value="434")
        diag_2 = st.text_input("diag_2", value="250.52")
        diag_3 = st.text_input("diag_3", value="250.42")
    with c8:
        number_diagnoses = st.number_input("number_diagnoses", value=9, step=1)
        max_glu_serum = st.text_input('max_glu_serum (e.g., "None", ">200")', value="")
        A1Cresult = st.text_input('A1Cresult (e.g., "None", ">7")', value="")

    st.subheader("Medications")
    # Usamos un expansor para no saturar la vista
    with st.expander("Ver lista de medicamentos"):
        med_cols = st.columns(3)
        meds = ["metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride", 
                "acetohexamide", "glipizide", "glyburide", "tolbutamide", "pioglitazone", 
                "rosiglitazone", "acarbose", "miglitol", "troglitazone", "tolazamide", 
                "examide", "citoglipton", "insulin"]
        med_values = {}
        for i, med in enumerate(meds):
            with med_cols[i % 3]:
                med_values[med] = st.selectbox(med, options=MED_DIRS, key=med)

    st.subheader("Combo Meds & Flags")
    c9, c10 = st.columns(2)
    with c9:
        glyburide_metformin = st.number_input("glyburide_metformin", value=0.0)
        glipizide_metformin = st.number_input("glipizide_metformin", value=0.0)
        glimepiride_pioglitazone = st.number_input("glimepiride_pioglitazone", value=0.0)
    with c10:
        metformin_rosiglitazone = st.number_input("metformin_rosiglitazone", value=0.0)
        metformin_pioglitazone = st.number_input("metformin_pioglitazone", value=0.0)
        change_m = st.number_input("change_m", value=0.0)
        diabetesMed = st.selectbox('diabetesMed', options=["YES", "NO"], index=0)

    predict_btn = st.button("🚀 Predict", type="primary", use_container_width=True)

# --- Construcción del Payload ---
payload = {
    "encounter_id": _int_or_none(encounter_id),
    "patient_nbr": _int_or_none(patient_nbr),
    "race": race,
    "gender": gender,
    "age": age,
    "weight": _none_if_empty(weight),
    "admission_type_id": _int_or_none(admission_type_id),
    "discharge_disposition_id": _int_or_none(discharge_disposition_id),
    "admission_source_id": _int_or_none(admission_source_id),
    "time_in_hospital": _int_or_none(time_in_hospital),
    "payer_code": _none_if_empty(payer_code),
    "medical_specialty": _none_if_empty(medical_specialty),
    "num_lab_procedures": _int_or_none(num_lab_procedures),
    "num_procedures": _int_or_none(num_procedures),
    "num_medications": _int_or_none(num_medications),
    "number_outpatient": _int_or_none(number_outpatient),
    "number_emergency": _int_or_none(number_emergency),
    "number_inpatient": _int_or_none(number_inpatient),
    "diag_1": _none_if_empty(diag_1),
    "diag_2": _none_if_empty(diag_2),
    "diag_3": _none_if_empty(diag_3),
    "number_diagnoses": _int_or_none(number_diagnoses),
    "max_glu_serum": _none_if_empty(max_glu_serum) if max_glu_serum else "",
    "A1Cresult": _none_if_empty(A1Cresult) if A1Cresult else "",
    **med_values,
    "glyburide_metformin": _float_or_zero(glyburide_metformin),
    "glipizide_metformin": _float_or_zero(glipizide_metformin),
    "glimepiride_pioglitazone": _float_or_zero(glimepiride_pioglitazone),
    "metformin_rosiglitazone": _float_or_zero(metformin_rosiglitazone),
    "metformin_pioglitazone": _float_or_zero(metformin_pioglitazone),
    "change_m": _float_or_zero(change_m),
    "diabetesMed": diabetesMed,
}

# --- Columna de Salida ---
with col_output:
    st.subheader("Request preview")
    st.json(payload)

    st.subheader("Response from API")
    if predict_btn:
        with st.spinner("Calling API..."):
            resp_json, summary, status_info = predict_request(payload)
            st.markdown(summary)
            st.json(resp_json)
            st.code(status_info)
    else:
        st.info("Waiting for prediction...")

# --- Acordeón para cURL ---
with st.expander("cURL example"):
    curl_str = f"""curl -X POST {API_URL} \\
  -H 'Content-Type: application/json' \\
  -d '{json.dumps(payload, ensure_ascii=False)}'"""
    st.code(curl_str, language="bash")