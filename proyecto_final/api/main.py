from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Response, BackgroundTasks
from dto.model_prediction_request import ModelPredictionRequest, NORMALIZED_COLUMNS
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import mlflow
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv
import cloudpickle
import shutil
import pandas as pd
import joblib
import numpy as np
import datetime
import json
import time
import random
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODEL_STAGE = os.getenv("MODEL_STAGE", "prod")
MODELS_DIR = os.environ.get("MODELS_DIR","/app/models")
MODEL_NAME = os.getenv("MODEL_NAME", "diabetes-model")
MODEL_PATH = os.path.join(MODELS_DIR, f"model_{MODEL_NAME}.pkl")
PREP_PATH = os.path.join(MODELS_DIR, f"preprocessor.pkl")
PREP = None
GROUPS = None  # optional if you want to backfill missing columns
MODEL = None


# --- DB Configuration for Inference Logs ---
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "mysql_db")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "training")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(
    DATABASE_URL,
    pool_size=100,
    max_overflow=50,
    pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InferenceLog(Base):
    __tablename__ = "inference_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    input_data = Column(Text)
    prediction = Column(Integer)
    probability = Column(Float, nullable=True)
    model_name = Column(String(100))
    model_version = Column(String(50))
    latency_ms = Column(Float)
    request_id = Column(String(100))

# Create table if it doesn't exist
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global PREP, GROUPS, MODEL
    print("Loading resources at startup...")
    
    # Load preprocessor
    if os.path.exists(PREP_PATH):
        try:
            with open(PREP_PATH, "rb") as f:
                payload = cloudpickle.load(f)
            PREP = payload.get("prep")
            GROUPS = payload.get("groups")
            print("Preprocessor loaded successfully from local file.")
        except Exception as e:
            print(f"Error loading preprocessor from file at startup: {e}")
            
    # Load model
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
            MODEL = mlflow.pyfunc.load_model(model_uri)
            print("Model loaded successfully from MLflow.")
            MODEL_INFO.info({'model_name': MODEL_NAME, 'stage': MODEL_STAGE, 'sync_time': 'mlflow_startup'})
        except Exception as e:
            print(f"Could not load model from MLflow at startup: {e}")
            
    yield  # <-- this yields control to the app runtime
    print("Cleaning up resources at shutdown...")

app = FastAPI(title="Diabetes API", version="1.0", lifespan=lifespan)


@app.get("/models")
def get_models():
    return {"available_models": ["random_forest"]}
         


def normalize_request(req: ModelPredictionRequest):
    global PREP, GROUPS

    if PREP is None:
        if os.path.exists(PREP_PATH):
            print("Loading preprocessor on demand...")
            with open(PREP_PATH, "rb") as f:
                payload = cloudpickle.load(f)
            PREP = payload["prep"]
            GROUPS = payload.get("groups")
        else:
            raise HTTPException(500, "Preprocessor not loaded")
            
    data_dict = req.model_dump()
    df = pd.DataFrame([data_dict])
    X_new = PREP.transform(df)
    feature_names = PREP.get_feature_names_out()
    X_new = pd.DataFrame(X_new, columns=feature_names)
    X_new = X_new[NORMALIZED_COLUMNS]
    print("X_new in normalize_request", X_new)
    # Convert to plain Python so FastAPI can serialize it
    return X_new

REQUEST_COUNT = Counter('predict_requests_total', 'Total de peticiones de predicción', ['status'])
REQUEST_LATENCY = Histogram('predict_latency_seconds', 'Tiempo de latencia de predicción')
PREDICTION_DIST = Counter('prediction_output_total', 'Distribución de resultados de predicción', ['output'])
MODEL_INFO = Info('model_metadata', 'Metadatos del modelo cargado')

def save_log_to_db(req_data, prediction_val, prob_val, latency_val, request_id_val):
    db = SessionLocal()
    try:
        log_entry = InferenceLog(
            input_data=json.dumps(req_data),
            prediction=int(prediction_val),
            probability=prob_val,
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

@app.post("/predict")
def predict_model(
    req: ModelPredictionRequest,
    background_tasks: BackgroundTasks,
    X_new_df: pd.DataFrame = Depends(normalize_request)
):
    global MODEL
    start_time = time.time()
    try:
        with REQUEST_LATENCY.time():
            # Keep a small simulated delay for realistic metrics, but low to support high concurrency
            time.sleep(random.uniform(0.01, 0.05))
            
        if MODEL is None:
            if os.path.exists(MODEL_PATH):
                print("Loading model on demand from local file...")
                MODEL = joblib.load(MODEL_PATH)
            else:
                print("Local model file not found, loading from MLflow...")
                model_uri = f"models:/{MODEL_NAME}@{MODEL_STAGE}"
                MODEL = mlflow.pyfunc.load_model(model_uri)

        if MODEL is None:
            raise HTTPException(status_code=404, detail=f"Model {MODEL_NAME} not loaded.")

        print(f"Predicting with cached model")
        prediction = MODEL.predict(X_new_df)
            
        # Get probability if available
        prob = None
        if hasattr(MODEL, "predict_proba"):
            prob = float(np.max(MODEL.predict_proba(X_new_df)))
        elif hasattr(MODEL, "_model_impl") and hasattr(MODEL._model_impl, "predict_proba"):
            try:
                prob = float(np.max(MODEL._model_impl.predict_proba(X_new_df)))
            except Exception:
                pass

        latency = (time.time() - start_time) * 1000
        
        # --- Save Inference Log Asynchronously ---
        REQUEST_COUNT.labels(status='success').inc()
        PREDICTION_DIST.labels(output=str(prediction[0])).inc()
        
        request_id = str(uuid.uuid4())
        background_tasks.add_task(
            save_log_to_db,
            req.model_dump(),
            prediction[0],
            prob,
            latency,
            request_id
        )

        print("prediction in predict_model", prediction)
        return {
            "prediction": int(prediction[0]),
            "probability": prob,
            "model": MODEL_NAME,
            "version": MODEL_STAGE,
            "latency_ms": latency,
            "features": X_new_df.to_numpy().tolist()
        }
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(status='error').inc()
        print("ERROR during prediction:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/model/{model_name}")
def load_model(model_name: str):
    return {"message": f"Model {model_name} loaded successfully"}

@app.post("/model")
async def save_model():
    global MODEL
    mlflow_model_url=f"models:/{MODEL_NAME}@{MODEL_STAGE}"
    print("mlflow_model_url ", mlflow_model_url)
    model = mlflow.sklearn.load_model(mlflow_model_url)

    if os.path.exists(MODEL_PATH):
        print(f"Model {MODEL_PATH} already exists, moving to {MODEL_PATH}.bak")
        shutil.move(MODEL_PATH, MODEL_PATH + ".bak")
    MODEL_INFO.info({'model_name': MODEL_NAME, 'stage': MODEL_STAGE, 'sync_time': str(datetime.datetime.now())})
    joblib.dump(model, MODEL_PATH)
    MODEL = model  # Update active global cache in-memory
    print("Model refreshed in global memory cache.")
    return {"message": f"Model {MODEL_NAME} saved and reloaded in memory successfully"}

@app.post("/upload_preprocessor")
async def upload_preprocessor(file: UploadFile = File(...)):
    global PREP, GROUPS
    # Ensure the model directory exists
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Check if preprocessor.pkl exists
    if os.path.exists(PREP_PATH):
        backup_file = PREP_PATH + ".bak"
        try:
            shutil.move(PREP_PATH, backup_file)
            print(f"Existing file moved to {backup_file}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")

    # Save the uploaded file as preprocessor.pkl
    try:
        with open(PREP_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving new file: {str(e)}")
    finally:
        file.file.close()

    # Reload the preprocessor into global memory cache
    try:
        with open(PREP_PATH, "rb") as f:
            payload = cloudpickle.load(f)
        PREP = payload.get("prep")
        GROUPS = payload.get("groups")
        print("Preprocessor reloaded globally in memory cache.")
    except Exception as e:
        print(f"Error loading uploaded preprocessor into memory: {e}")

    return {"message": "Preprocessor uploaded, saved, and reloaded globally."}
    
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/model-info")
def model_info():
    info = {
        "model_name": MODEL_NAME,
        "model_stage": MODEL_STAGE,
        "model_path": MODEL_PATH,
        "exists": os.path.exists(MODEL_PATH)
    }
    if info["exists"]:
        mtime = os.path.getmtime(MODEL_PATH)
        info["last_sync"] = datetime.datetime.fromtimestamp(mtime).isoformat()
    
    return info

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
