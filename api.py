from fastapi import FastAPI
from pydantic import BaseModel
import joblib 
import numpy as np

app = FastAPI()
modelo = joblib.load("modelo.pkl")

# Definiendo un modelo de datos
class Item(BaseModel):
    island:int
    bill_length_mm:float
    bill_depth_mm:float
    flipper_length_mm:int
    body_mass_g:int
    sex:int

@app.post("/items/")
def create_item(item: Item):
    X = np.array([[
        item.island,
        item.bill_length_mm,
        item.bill_depth_mm,
        item.flipper_length_mm,
        item.body_mass_g,
        item.sex
    ]]).reshape(-1, 1)
    pred = modelo.predict(X)
    return {"prediction": pred.tolist()}