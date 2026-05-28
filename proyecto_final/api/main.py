from fastapi import FastAPI, HTTPException, Response, BackgroundTasks
from dto.model_prediction_request import ModelPredictionRequest
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
import mlflow
from mlflow import MlflowClient
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv
import shutil
import pandas as pd
import joblib
import numpy as np
import datetime
import json
import time as time_module
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODEL_STAGE = os.getenv("MODEL_STAGE", "prod")
MODELS_DIR = os.environ.get("MODELS_DIR","/app/models")
MODEL_NAME = os.getenv("MODEL_NAME", "real-estate-model")
MODEL_PATH = os.path.join(MODELS_DIR, f"model_{MODEL_NAME}.pkl")
MODEL = None

# --- DB Configuration for Inference Logs ---
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "mysql_db")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "training")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_size=100, max_overflow=50, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InferenceLog(Base):
    __tablename__ = "inference_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    input_data = Column(Text)
    prediction = Column(Float)
    model_name = Column(String(100))
    model_version = Column(String(50))
    latency_ms = Column(Float)
    request_id = Column(String(100))

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODEL
    print("Loading resources at startup...")
    if os.path.exists(MODEL_PATH):
        try:
            MODEL = joblib.load(MODEL_PATH)
            print("Model loaded successfully from local file.")
            MODEL_INFO.info({'model_name': MODEL_NAME, 'stage': MODEL_STAGE, 'sync_time': 'startup'})
        except Exception as e:
            print(f"Error loading model from file at startup: {e}")
    else:
        print("Local model file not found at startup. Will try to fetch from MLflow...")
        try:
            model_uri = f"models:/{MODEL_NAME}@{MODEL_STAGE}"
            MODEL = mlflow.sklearn.load_model(model_uri)
            print("Model loaded successfully from MLflow.")
            MODEL_INFO.info({'model_name': MODEL_NAME, 'stage': MODEL_STAGE, 'sync_time': 'mlflow_startup'})
        except Exception as e:
            print(f"Could not load model from MLflow at startup: {e}")
    yield
    print("Cleaning up resources at shutdown...")

app = FastAPI(title="Real Estate API", version="1.0", lifespan=lifespan)

REQUEST_COUNT = Counter('predict_requests_total', 'Total de peticiones de prediccion', ['status'])
REQUEST_LATENCY = Histogram('predict_latency_seconds', 'Tiempo de latencia de prediccion')
PREDICTION_DIST = Counter('prediction_output_total', 'Distribucion de resultados de prediccion', ['output'])
MODEL_INFO = Info('model_metadata', 'Metadatos del modelo cargado')

INPUT_COLUMNS = [
    "brokered_by", "status", "bed", "bath", "acre_lot",
    "street", "city", "state", "zip_code", "house_size", "prev_sold_date",
]

def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["brokered_by"] = df["brokered_by"].fillna(0)
    df["bed"] = df["bed"].fillna(df["bed"].median())
    df["bath"] = df["bath"].fillna(df["bath"].median())
    df["acre_lot"] = df["acre_lot"].fillna(df["acre_lot"].median())
    df["street"] = df["street"].fillna(0)
    df["zip_code"] = df["zip_code"].fillna(0)
    df["house_size"] = df["house_size"].fillna(df["house_size"].median())
    df["status"] = df["status"].fillna("unknown")
    df["city"] = df["city"].fillna("unknown")
    df["state"] = df["state"].fillna("unknown")
    df["prev_sold_date"] = df["prev_sold_date"].fillna("")
    df["price_per_sqft"] = 0.0
    df["room_total"] = df["bed"] + df["bath"]
    df["has_prev_sold"] = (df["prev_sold_date"] != "").astype(int)
    return df

def save_log_to_db(req_data, prediction_val, latency_val, request_id_val):
    db = SessionLocal()
    try:
        log_entry = InferenceLog(
            input_data=json.dumps(req_data),
            prediction=float(prediction_val),
            model_name=MODEL_NAME,
            model_version=MODEL_STAGE,
            latency_ms=latency_val,
            request_id=request_id_val
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"Error saving inference log: {e}")
    finally:
        db.close()

@app.get("/models")
def get_models():
    return {"available_models": ["random_forest"]}

@app.post("/predict")
def predict_model(
    req: ModelPredictionRequest,
    background_tasks: BackgroundTasks,
):
    global MODEL
    start_time = time_module.time()
    try:
        with REQUEST_LATENCY.time():
            if MODEL is None:
                if os.path.exists(MODEL_PATH):
                    print("Loading model on demand from local file...")
                    MODEL = joblib.load(MODEL_PATH)
                else:
                    print("Local model file not found, loading from MLflow...")
                    model_uri = f"models:/{MODEL_NAME}@{MODEL_STAGE}"
                    MODEL = mlflow.sklearn.load_model(model_uri)

            if MODEL is None:
                raise HTTPException(status_code=404, detail=f"Model {MODEL_NAME} not loaded.")

            data_dict = req.model_dump()
            df = pd.DataFrame([data_dict])
            df = _engineer_features(df)

            prediction = MODEL.predict(df)

        latency = (time_module.time() - start_time) * 1000

        REQUEST_COUNT.labels(status='success').inc()
        PREDICTION_DIST.labels(output=str(round(float(prediction[0]), 2))).inc()

        request_id = str(uuid.uuid4())
        background_tasks.add_task(
            save_log_to_db,
            req.model_dump(),
            float(prediction[0]),
            latency,
            request_id
        )

        return {
            "prediction": float(prediction[0]),
            "model": MODEL_NAME,
            "version": MODEL_STAGE,
            "latency_ms": latency,
        }
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(status='error').inc()
        print("ERROR during prediction:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/model")
async def save_model():
    global MODEL
    mlflow_model_url = f"models:/{MODEL_NAME}@{MODEL_STAGE}"
    print("mlflow_model_url ", mlflow_model_url)
    model = mlflow.sklearn.load_model(mlflow_model_url)

    if os.path.exists(MODEL_PATH):
        print(f"Model {MODEL_PATH} already exists, moving to {MODEL_PATH}.bak")
        shutil.move(MODEL_PATH, MODEL_PATH + ".bak")
    MODEL_INFO.info({'model_name': MODEL_NAME, 'stage': MODEL_STAGE, 'sync_time': str(datetime.datetime.now())})
    joblib.dump(model, MODEL_PATH)
    MODEL = model
    print("Model refreshed in global memory cache.")
    return {"message": f"Model {MODEL_NAME} saved and reloaded in memory successfully"}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/model-info")
def model_info():
    info = {
        "model_name": MODEL_NAME,
        "model_stage": MODEL_STAGE,
        "model_path": MODEL_PATH,
        "exists": os.path.exists(MODEL_PATH),
    }
    if info["exists"]:
        mtime = os.path.getmtime(MODEL_PATH)
        info["last_sync"] = datetime.datetime.fromtimestamp(mtime).isoformat()
    try:
        client = MlflowClient()
        mv = client.get_model_version_by_alias(MODEL_NAME, MODEL_STAGE)
        info["version"] = mv.version
        info["run_id"] = mv.run_id
        info["status"] = mv.status
    except Exception:
        info["version"] = None
        info["run_id"] = None
        info["status"] = "not_found"
    return info

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
