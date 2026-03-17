# Imports necesarios para carga, visualización y particionado de datos
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from numpy.random import RandomState
import joblib
from datetime import datetime
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns
import requests

"""
Borra la base de datos 'covertype_db' en MySQL.
"""
def delete_database():
    print("="*50)
    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/"
    )
    with engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS covertype_db"))
    print("Base de datos 'covertype_db' borrada correctamente.")
    print("="*50)


"""
Consulta el API en localhost:8089 para obtener datos del lote actual y los almacena en MySQL.
"""
def fetch_api_and_store(group_number=9):
    # URL del API según el docker-compose de P2
    url = f"http://fastapi:8889/data?group_number={group_number}"
    
    print(f"Consultando API: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
    except Exception as e:
        print(f"Error al consultar el API: {e}")
        return

    # Extraer los datos de la respuesta
    batch_number = json_data.get("batch_number")
    raw_data = json_data.get("data", [])
    
    if not raw_data:
        print("No se recibieron datos del API.")
        return

    print(f"Batch {batch_number} recibido con {len(raw_data)} filas.")

    # si batch_number es 9, reiniciar el contador en el api
    if batch_number == 9:
        url = f"http://fastapi:8889/restart_data_generation?group_number={group_number}"

        print(f"Reiniciando API: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            json_data = response.json() # respuesta del api
            print("API reiniciada correctamente.", json_data)
        except Exception as e:
            print(f"Error al reiniciar el API: {e}")
            return


    # Columnas definidas del API
    columns = [
        "Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology", 
        "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways", 
        "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm", 
        "Horizontal_Distance_To_Fire_Points", "Wilderness_Area", 
        "Soil_Type", "Cover_Type"
    ]
    df = pd.DataFrame(raw_data, columns=columns)

    # Escritura en MySQL   
    try:
        # Asegurar que la DB existe
        engine = create_engine(f"mysql+pymysql://root:root123@mysql:3306/")
        with engine.connect() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS covertype_db"))
            conn.execute(text("COMMIT"))
        
        # Conectar a la DB
        db_engine = create_engine(f"mysql+pymysql://root:root123@mysql:3306/covertype_db")
        
        # Almacenar los datos en la tabla 'raw' de manera incremental
        df.to_sql(
            name="raw",
            con=db_engine,
            if_exists="append",
            index=False
        )
        
        print(f"Datos almacenados correctamente en covertype_db.raw")
        print("="*50)
        
    except Exception as e:
        print(f"Error al interactuar con MySQL: {e}")

