from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import joblib,boto3,os
import numpy as np
import requests

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
    Elevation: int
    Aspect: int
    Slope: int
    Horizontal_Distance_To_Hydrology: int
    Vertical_Distance_To_Hydrology: int
    Horizontal_Distance_To_Roadways: int
    Hillshade_9am: int
    Hillshade_Noon: int
    Hillshade_3pm: int
    Horizontal_Distance_To_Fire_Points: int
    Wilderness_Area: str
    Soil_Type: str
    modelo: str # Se agrega el parametro de modelo al realizar la petición de predicción

def descargarArchivo(url):
    nombre = url.split("/")
    response = requests.get(url)
    path = "/tmp/"+nombre[-1]
    open(path, "wb").write(response.content)
    return path

"""
    Se define una petición tipo post para recibir los 
    parametros de entrada para que el modelo previamente
    entrenado pueda predecir el resultado
"""
@app.post("/items/")
def create_item(item: Item):
    if item.modelo in listar_modelos():
        X = np.array([[
            item.Elevation,
            item.Aspect,
            item.Slope,
            item.Horizontal_Distance_To_Hydrology,
            item.Vertical_Distance_To_Hydrology,
            item.Horizontal_Distance_To_Roadways,
            item.Hillshade_9am,
            item.Hillshade_Noon,
            item.Hillshade_3pm,
            item.Horizontal_Distance_To_Fire_Points,
            item.Wilderness_Area,
            item.Soil_Type
        ]])

        endpoint = os.getenv('MINIO_ENDPOINT', 'http://minio:9000')
        bucket = 'modelos'
        # Descargar modelo de minio en /tmp
        path = descargarArchivo(f"{endpoint}/{bucket}/{item.modelo}")

        modelo = joblib.load(path)
        pred = modelo.predict(X)
        return {"prediction": pred.tolist()} # Se retorna el resultado
    else:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")