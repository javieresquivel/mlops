from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import joblib,boto3,os
import numpy as np

app = FastAPI()
MODELS_DIR = Path("/app/models")

def listar_modelos():
    #return [f.name for f in MODELS_DIR.iterdir() if f.is_file()]
    endpoint = os.getenv('MINIO_ENDPOINT', 'http://minio:9000')
    access_key = os.getenv('AWS_ACCESS_KEY_ID', 'admin')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'supersecret')
    bucket = 'modelos'
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    )
    response = s3.list_objects_v2(Bucket=bucket)
    return [item['Key'] for item in response.get('Contents', [])]

"""
    Se listan los modelos o archivos presentes en el volumen compartido
    entre los dos contenedores para que el usuario pueda decidir cual usar y 
    se define la ruta /model en el api para tal fin
"""
@app.get("/models")
def obtener_modelos():
    modelos = listar_modelos()
    return {"modelos": modelos}

"""
    Se define el modelo de datos con  base 
    a las columnas usadas de la base de datos de 
    pinguinos excluyendo las columnas que no se van 
    a tener en cuenta
"""
class Item(BaseModel):
    island:int
    bill_length_mm:float
    bill_depth_mm:float
    flipper_length_mm:int
    body_mass_g:int
    sex:int
    modelo:str # Se agregar el parametro de modelo al realizar la petición de predicción

"""
    Se define una petición tipo post para recibir los 
    parametros de entrada para que el modelo previamente
    entrenado pueda predecir el resultado
"""
@app.post("/items/")
def create_item(item: Item):
    if item.modelo in listar_modelos():
        X = np.array([[
            item.island,
            item.bill_length_mm,
            item.bill_depth_mm,
            item.flipper_length_mm,
            item.body_mass_g,
            item.sex
        ]])
        modelo = joblib.load(f"/app/models/{item.modelo}")
        pred = modelo.predict(X)
        return {"prediction": pred.tolist()} # Se retorna el resultado
    else:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")