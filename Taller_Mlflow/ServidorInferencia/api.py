from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import joblib,boto3,os
import mlflow.pyfunc
import numpy as np
import requests

app = FastAPI()
MODELS_DIR = Path("/app/models")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

@app.on_event("startup")
def load_model():
    global model
    model_name = "produccion"
    alias = "pro"
    model_uri = f"models:/{model_name}@{alias}"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"Modelo {model_name} (Producción) cargado exitosamente.")

class Item(BaseModel):
    island:int
    bill_length_mm:float
    bill_depth_mm:float
    flipper_length_mm:int
    body_mass_g:int
    sex:int

@app.post("/predict")
def predict(item: Item):
    X = np.array([[
        item.island,
        item.bill_length_mm,
        item.bill_depth_mm,
        item.flipper_length_mm,
        item.body_mass_g,
        item.sex
    ]])
    pred = model.predict(X)
    return {"prediction": pred.tolist()} # Se retorna el resultado