import streamlit as st
import pandas as pd
import sys
sys.path.insert(0, "..")
from utils import fetch_inference_logs

st.set_page_config(page_title="Historial de Inferencias", page_icon="📋", layout="wide")
st.title("📋 Historial de inferencias")

with st.spinner("Cargando inferencias desde la base de datos..."):
    try:
        df = fetch_inference_logs()
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

if df.empty:
    st.info("Aún no hay predicciones registradas. Usa el formulario de inferencia para generar la primera.")
    st.stop()

total = len(df)
pred_promedio = df["prediction"].mean()
latencia_promedio = df["latency_ms"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Total inferencias", total)
col2.metric("Precio promedio", f"${pred_promedio:,.2f}" if pd.notna(pred_promedio) else "—")
col3.metric("Latencia promedio", f"{latencia_promedio:.1f} ms" if pd.notna(latencia_promedio) else "—")

st.markdown("---")

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

df_mostrar = df.rename(columns={
    "timestamp": "Fecha",
    "input_data": "Datos de entrada",
    "prediction": "Precio predicho",
    "model_name": "Modelo",
    "model_version": "Versión",
    "latency_ms": "Latencia (ms)",
    "request_id": "Request ID",
})

df_mostrar["Precio predicho"] = df_mostrar["Precio predicho"].apply(
    lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
)
df_mostrar["Latencia (ms)"] = df_mostrar["Latencia (ms)"].apply(
    lambda x: f"{x:.1f}" if pd.notna(x) else "—"
)

COLUMNAS = ["Fecha", "Precio predicho", "Modelo", "Versión", "Latencia (ms)", "Datos de entrada", "Request ID"]
columnas_reales = [c for c in COLUMNAS if c in df_mostrar.columns]
df_mostrar = df_mostrar[columnas_reales]

st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

st.markdown("---")
with st.expander("Ver datos de entrada completos"):
    for _, row in df.head(20).iterrows():
        fecha = row.get("timestamp", "")
        pred = row.get("prediction", "")
        input_data = row.get("input_data", "")
        st.markdown(f"**{fecha}** — Predicción: ${pred:,.2f}" if pd.notna(pred) else f"**{fecha}**")
        st.code(input_data, language="json")
        st.markdown("---")
