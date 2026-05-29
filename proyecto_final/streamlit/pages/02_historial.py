import streamlit as st
import pandas as pd
import sys
sys.path.insert(0, "..")
from utils import fetch_training_history

st.set_page_config(page_title="Historial", page_icon="📊", layout="wide")
st.title("📊 Historial de entrenamientos")

with st.spinner("Cargando historial desde la base de datos..."):
    try:
        df = fetch_training_history()
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

if df.empty:
    st.info("No hay registros de entrenamiento aún. Ejecuta el DAG para generar el primer historial.")
    st.stop()

st.markdown(f"**{len(df)}** ejecuciones registradas")

with st.sidebar:
    st.header("Filtros")

    decisiones = ["Todas"] + sorted(df["decision"].dropna().unique().tolist())
    filtro_decision = st.selectbox("Decisión", decisiones)

    if "execution_date" in df.columns and not df["execution_date"].isna().all():
        df["execution_date"] = pd.to_datetime(df["execution_date"], errors="coerce")
        fechas = df["execution_date"].dropna()
        if not fechas.empty:
            fecha_min = fechas.min().to_pydatetime()
            fecha_max = fechas.max().to_pydatetime()
            filtro_fecha = st.date_input(
                "Rango de fechas",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max,
            )

if filtro_decision != "Todas":
    df = df[df["decision"] == filtro_decision]

if "execution_date" in df.columns:
    df = df.sort_values("execution_date", ascending=False)

COLUMNS_MOSTRAR = [
    "batch_number", "execution_date", "decision", "model_version",
    "candidate_mae", "candidate_rmse", "candidate_r2",
    "mae_improvement_pct", "rmse_regression_pct",
    "reason", "mlflow_run_id",
]

columnas_reales = [c for c in COLUMNS_MOSTRAR if c in df.columns]
df_mostrar = df[columnas_reales].copy()

RENOMBRES = {
    "batch_number": "Lote",
    "execution_date": "Fecha",
    "decision": "Decisión",
    "model_version": "Versión modelo",
    "candidate_mae": "MAE candidato",
    "candidate_rmse": "RMSE candidato",
    "candidate_r2": "R² candidato",
    "mae_improvement_pct": "Mejora MAE (%)",
    "rmse_regression_pct": "Regresión RMSE (%)",
    "reason": "Razón",
    "mlflow_run_id": "MLflow Run ID",
}
df_mostrar = df_mostrar.rename(columns=RENOMBRES)

def color_decision(val):
    if val == "promoted":
        return "background-color: #d4edda; color: #155724"
    elif val == "rejected":
        return "background-color: #f8d7da; color: #721c24"
    elif val == "skip":
        return "background-color: #e2e3e5; color: #383d41"
    return ""

styled = df_mostrar.style.map(color_decision, subset=["Decisión"])
styled = styled.format({
    "MAE candidato": lambda x: f"{x:.2f}" if pd.notna(x) else "—",
    "RMSE candidato": lambda x: f"{x:.2f}" if pd.notna(x) else "—",
    "R² candidato": lambda x: f"{x:.4f}" if pd.notna(x) else "—",
    "Mejora MAE (%)": lambda x: f"{x:.2f}%" if pd.notna(x) else "—",
    "Regresión RMSE (%)": lambda x: f"{x:.2f}%" if pd.notna(x) else "—",
})

st.dataframe(styled, use_container_width=True, hide_index=True)
