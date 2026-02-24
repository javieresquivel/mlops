from fastapi import FastAPI
from pydantic import BaseModel
import joblib 
import numpy as np

app = FastAPI()
modelo = joblib.load("modelo.pkl")

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

"""
    Se define una petición tipo post para recibir los 
    parametros de entrada para que el modelo previamente
    entrenado pueda predecir el resultado
"""
@app.post("/items/")
def create_item(item: Item):
    X = np.array([[
        item.island,
        item.bill_length_mm,
        item.bill_depth_mm,
        item.flipper_length_mm,
        item.body_mass_g,
        item.sex
    ]])
    pred = modelo.predict(X)
    return {"prediction": pred.tolist()} # Se retorna el resultado