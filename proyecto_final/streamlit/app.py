import streamlit as st

st.set_page_config(
    page_title="MLOps — Real Estate",
    page_icon="🏠",
    layout="centered",
)

st.sidebar.title("MLOps Grupo 9")
st.sidebar.markdown("Javier Esquivel · Santiago Serrano")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Inicio", icon="🏠")
st.sidebar.page_link("pages/01_inferencia.py", label="Inferencia", icon="🔮")
st.sidebar.page_link("pages/02_historial.py", label="Historial", icon="📊")
st.sidebar.page_link("pages/03_historial_inferencias.py", label="Inferencias registradas", icon="📋")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "Pipeline de ingesta, validación, entrenamiento y despliegue "
    "para regresión de precios de propiedades inmobiliarias."
)

st.title("MLOps — Proyecto Final")
st.markdown(
    """
    Este sistema implementa un pipeline completo de MLOps para
    **regresión de precios de propiedades inmobiliarias**.

    - **Inferencia**: formulario para predecir el precio de una propiedad.
    - **Historial**: seguimiento de cada ejecución del DAG de entrenamiento.
    - **Inferencias registradas**: log de todas las predicciones realizadas por la API.
    """
)

col1, col2 = st.columns(2)
col1.metric("Modelo", "Random Forest")
col2.metric("Dataset", "12 variables · lotes API")
