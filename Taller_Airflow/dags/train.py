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

"""
Borra la base de datos 'penguins' en MySQL.
"""
def delete_database():
    print("="*50)
    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/"
    )
    with engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS penguins"))
    print("Base de datos 'penguins' borrada correctamente.")
    print("="*50)



"""
Carga el CSV en la BBDD Penguins en la tabla RAW
"""
def load_csv_to_mysql(csv_path):
    print("="*50)
    # Conexión a MySQL
    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/"
    )

    # Crear base de datos si no existe
    with engine.connect() as conn:
        conn.execute(text("CREATE DATABASE IF NOT EXISTS penguins"))
        conn.execute(text("COMMIT"))
    
    # Conectar a la base penguins
    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/penguins"
    )

    # Leer CSV
    df = pd.read_csv(csv_path)

    # Guardar en tabla raw
    df.to_sql(
        name="raw",
        con=engine,
        if_exists="replace",
        index=False
    )

    print("Datos cargados correctamente en penguins.raw")
    print("="*50)


"""
Lee la tabla 'raw' de la base de datos 'penguins', realiza limpieza básica, transformación de variables categóricas y guarda el DataFrame resultante en la tabla 'transform' de la misma base de datos.
"""
def preprocess():
    print("="*50)
    #Lee la tabla 'raw' de la base de datos 'penguins' y retorna un DataFrame.

    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/penguins"
    )
    df = pd.read_sql("SELECT * FROM raw", con=engine)
    print("Datos leídos correctamente desde penguins.raw")

    print("Primeras filas del DataFrame:")
    print(df.head())

    # Inspección inicial y limpieza básica (mostrar estructura y eliminar filas con NA)
    df_clean = df.dropna()
    # Limpieza de columnas irrelevantes y comprobación de NA después de limpiar
    df_clean.drop('Unnamed: 0', axis=1, inplace=True)
    df_clean = df_clean.drop(columns=["year"])

    print("Datos limpios")

    # Preparar variables categóricas para modelado
    df_encoded = df_clean.copy()

    categorical_cols = df_encoded.select_dtypes(include=["object", "category"]).columns
    categorical_cols = [col for col in categorical_cols if col != "species"]

    for col in categorical_cols:
        le = LabelEncoder()
        df_encoded[col] = le.fit_transform(df_encoded[col])

    print("Datos transformados")

    # Guardar el DataFrame transformado en la tabla 'transform' de la base de datos 'penguins'
    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/penguins"
    )
    df_encoded.to_sql(
        name="transform",
        con=engine,
        if_exists="replace",
        index=False
    )
    print("Datos guardados en la tabla 'transform' de la base de datos penguins.")
    print("="*50)


"""
Lee el DataFrame transformado desde la tabla 'transform' de la base de datos 'penguins', separa características y objetivo, realiza partición train/test estratificada, entrena un modelo RandomForest, evalúa su desempeño y guarda el modelo entrenado en formato pkl.
"""
def train():
    print("="*50)
    # Leer el DataFrame transformado desde la tabla 'transform' de la base de datos 'penguins'
    engine = create_engine(
        "mysql+pymysql://root:root123@mysql:3306/penguins"
    )
    df_encoded = pd.read_sql("SELECT * FROM transform", con=engine)
    print("Datos leídos correctamente desde penguins.transform") 

    # Separar características (X) y objetivo (y) y crear partición train/test estratificada
    y = df_encoded["species"]
    X = df_encoded.drop(columns=["species"])

    print(f"Número de columnas de características: {X.shape[1]}")
    print(f"Columnas de características: {list(X.columns)}")
    print(f"\nDimensiones de X: {X.shape}  |  Dimensiones de y: {y.shape}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RandomState(42),
        stratify=y,
    )

    print(f"\nDimensiones del conjunto de entrenamiento: X_train={X_train.shape}, y_train={y_train.shape}")
    print(f"Dimensiones del conjunto de prueba:       X_test={X_test.shape}, y_test={y_test.shape}")
                                      
                                   
    # Construir un clasificador RandomForest simple

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    )
                        

    # Entrenar el modelo con los datos de entrenamiento
    model.fit(X_train, y_train)

    # Validación cruzada en entrenamiento (5-fold) para estimar estabilidad
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="accuracy", n_jobs=-1)
    print(f"\nCV (5-fold) - accuracy: mean={cv_scores.mean():.4f}, std={cv_scores.std():.4f}")



    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.4f}")
    print("\nReporte de clasificación:")
    print(classification_report(y_test, y_pred))

    # Matriz de confusión
    cm = confusion_matrix(y_test, y_pred)
    print("\nMatriz de confusión:")
    print(cm)


    # Guardar el modelo entrenado en formato pkl
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = f'/opt/airflow/dags/models/model_random_forest_{timestamp}.pkl'
    joblib.dump(model, model_path)
    print(f"Modelo guardado en: {model_path}")
    print("="*50)




##borrar la base de datos
#delete_database()
## Cargar datos del CSV a MySQL
#load_csv_to_mysql("./Data/penguins.csv")
## procesar los datos
#preprocess()
## Entrenar el modelo
#train()
