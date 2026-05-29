import streamlit as st
import sys
sys.path.insert(0, "..")
from utils import predict_price

st.set_page_config(page_title="Inferencia", page_icon="🔮", layout="centered")
st.title("🔮 Predecir precio de propiedad")

with st.form("prediction_form"):
    col1, col2 = st.columns(2)

    with col1:
        brokered_by = st.number_input(
            "Brokered by (ID corredor)", min_value=0, value=1, step=1
        )
        bed = st.number_input(
            "Dormitorios", min_value=0, max_value=50, value=3, step=1
        )
        bath = st.number_input(
            "Baños", min_value=0.0, max_value=50.0, value=2.0, step=0.5
        )
        acre_lot = st.number_input(
            "Tamaño del terreno (acres)", min_value=0.0, value=0.5, step=0.1
        )
        street = st.number_input(
            "Dirección (ID numérico)", min_value=0, value=100, step=1
        )
        zip_code = st.number_input(
            "Código postal", min_value=0, value=33101, step=1
        )

    with col2:
        status = st.selectbox(
            "Estado", options=["for_sale", "ready_to_build", "sold", "unknown"]
        )
        city = st.text_input("Ciudad", value="Miami")
        state = st.text_input("Estado", value="FL")
        house_size = st.number_input(
            "Tamaño de la casa (sqft)", min_value=0.0, value=1500.0, step=100.0
        )
        prev_sold_date = st.text_input(
            "Fecha de venta anterior (YYYY-MM-DD)", value=""
        )

    submitted = st.form_submit_button("Predecir precio", type="primary", use_container_width=True)

if submitted:
    data = {
        "brokered_by": brokered_by,
        "status": status,
        "bed": bed,
        "bath": bath,
        "acre_lot": acre_lot,
        "street": street,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "house_size": house_size,
        "prev_sold_date": prev_sold_date,
    }

    with st.spinner("Consultando modelo..."):
        try:
            result = predict_price(data)
            pred = result["prediction"]
            model = result.get("model", "—")
            version = result.get("version", "—")
            latency = result.get("latency_ms", 0)

            st.success("Predicción completada")
            cols = st.columns(3)
            cols[0].metric("Precio estimado", f"${pred:,.2f}")
            cols[1].metric("Modelo", model)
            cols[2].metric("Latencia", f"{latency:.1f} ms")
            with st.expander("Respuesta completa de la API"):
                st.json(result)
        except Exception as e:
            st.error(f"Error al predecir: {e}")
