from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Response
from dto.model_prediction_request import ModelPredictionRequest, NORMALIZED_COLUMNS
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import mlflow
import os
from pathlib import Path
from dotenv import load_dotenv
import cloudpickle
import shutil
import pandas as pd
import joblib
import numpy as np
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODEL_STAGE = os.getenv("MODEL_STAGE", "prod")
MODELS_DIR = os.environ.get("MODELS_DIR","/app/models")
MODEL_NAME = os.getenv("MODEL_NAME", "diabetes-model")
MODEL_PATH = os.path.join(MODELS_DIR, f"model_{MODEL_NAME}.pkl")
PREP_PATH = os.path.join(MODELS_DIR, f"preprocessor.pkl")
PREP = None
GROUPS = None  # optional if you want to backfill missing columns

@asynccontextmanager
async def lifespan(app: FastAPI):
    global PREP, GROUPS
    print("Loading preprocessor at startup...")
    
    print("Preprocessor loaded successfully")
    yield  # <-- this yields control to the app runtime
    print("Cleaning up resources at shutdown...")

app = FastAPI(title="Diabetes API", version="1.0", lifespan=lifespan)


@app.get("/models")
def get_models():
    return {"available_models": ["random_forest"]}
         


def normalize_request(req: ModelPredictionRequest):

    with open(PREP_PATH, "rb") as f:
        payload = cloudpickle.load(f)
    PREP = payload["prep"]
    GROUPS = payload.get("groups")

    if PREP is None:
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

REQUEST_COUNT = Counter('predict_requests_total', 'Total de peticiones de predicción')
REQUEST_LATENCY = Histogram('predict_latency_seconds', 'Tiempo de latencia de predicción')

@app.post("/predict")
async def predict_model(
    X_new_df: pd.DataFrame = Depends(normalize_request)
):
    try:
        import time
        import random
        REQUEST_COUNT.inc()
        with REQUEST_LATENCY.time():
            time.sleep(random.uniform(0.1, 0.3))
        # Convertimos el objeto request a un diccionario
        """
        model = joblib.load(MODEL_PATH)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Model {MODEL_NAME} not found.")
        """
        model_uri = f"models:/{MODEL_NAME}@{MODEL_STAGE}"
        model = mlflow.pyfunc.load_model(model_uri)

        print(f"Model {MODEL_NAME} loaded from {MODEL_PATH}")
        #features = normalized_req        
        prediction = model.predict(X_new_df)
        print("prediction in predict_model", prediction)
        return {
           "prediction": int(prediction[0]),
           "features": X_new_df.astype(float).to_numpy().tolist()
        }
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/model/{model_name}")
def load_model(model_name: str):
    return {"message": f"Model {model_name} loaded successfully"}

@app.post("/model")
async def save_model():
    mlflow_model_url=f"models:/{MODEL_NAME}@{MODEL_STAGE}"
    print("mlflow_model_url ", mlflow_model_url)
    model = mlflow.sklearn.load_model(mlflow_model_url)

    if os.path.exists(MODEL_PATH):
        print(f"Model {MODEL_PATH} already exists, moving to {MODEL_PATH}.bak")
        shutil.move(MODEL_PATH, MODEL_PATH + ".bak")
    joblib.dump(model, MODEL_PATH)
    return {"message": f"Model {MODEL_NAME} saved successfully"}

@app.post("/upload_preprocessor")
async def upload_preprocessor(file: UploadFile = File(...)):
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

    return {"message": "Preprocessor uploaded and saved successfully."}
    
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
