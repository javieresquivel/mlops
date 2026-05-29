import os
import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine, text

API_URL = os.getenv("API_URL", "http://api:8000")
DB_HOST = os.getenv("DB_HOST", "mysql_db")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "training")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_size=5, max_overflow=10)


def fetch_training_history():
    engine = get_engine()
    query = """
        SELECT
            batch_number,
            execution_date,
            decision,
            model_version,
            reason,
            candidate_mae,
            candidate_rmse,
            candidate_r2,
            production_version,
            production_mae,
            mae_improvement_pct,
            rmse_regression_pct,
            mlflow_run_id
        FROM training_history
        ORDER BY execution_date DESC
    """
    return pd.read_sql(query, engine)


def fetch_inference_logs(limit=500):
    engine = get_engine()
    query = f"""
        SELECT
            id,
            timestamp,
            input_data,
            prediction,
            model_name,
            model_version,
            latency_ms,
            request_id
        FROM inference_logs
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, engine)


def predict_price(data: dict) -> dict:
    resp = requests.post(f"{API_URL}/predict", json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()
