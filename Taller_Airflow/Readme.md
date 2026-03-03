# Pipeline de Machine Learning con Airflow y MySQL

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano
  
## 1. Implementación de Base de Datos y Modelo
**Base de Datos MySQL:** Se integró utilizando Docker Compose (`docker-compose.yml`). Se configuró un contenedor basado en la imagen `mysql:8.0`, exponiendo el puerto 3306 y usando un volumen para asegurar la persistencia de la información.
<img width="533" height="307" alt="image" src="https://github.com/user-attachments/assets/62a9aadc-d8f4-4bb1-94da-79c4158b7617" />

**Métodos de Procesamiento (`train.py`):**
*   **Borrar Base de Datos:** `delete_database()` emplea `sqlalchemy` para conectarse al servidor y ejecutar la consulta `DROP DATABASE` en caso de que la base de datos `penguins` ya exista, reiniciando así el entorno.
*   **Guardar Datos Raw:** `load_csv_to_mysql()` crea la base de datos `penguins`. Posterior a esto, usa la librería `pandas` para cargar el archivo original `penguins.csv` y volcarlo directamente en la tabla `raw`.
*   **Guardar Datos Transform:** `preprocess()` lee los datos de la tabla `raw`, limpia los registros nulos y remueve columnas innecesarias (como `year`). Aplica la transformación `LabelEncoder` del modelo `scikit-learn` a las variables categóricas, y finalmente almacena el conjunto tratado en la tabla `transform`.
*   **Guardado del Modelo:** `train()` recupera los registros desde la tabla `transform` y hace una partición de los datos para entrenamiento o prueba. Configura y entrena un `RandomForestClassifier`. Con el modelo ya entrenado y evaluado, utiliza la librería `joblib` para exportarlo (.pkl) con un sello de tiempo en su nombre, depositándolo de esa manera en el volumen mapeado a la carpeta `models`.

## 2. Implementación del DAG
El proceso de orquestación se implementó en `dags/dag_taller.py`. Se definió un DAG de nombre `penguins_ml_pipeline` integrado por cuatro tareas configuradas mediante `PythonOperator`:
1.  **`delete_database`**: Borra la base de datos previa.
2.  **`load_csv_to_mysql`**: Carga el CSV y genera la tabla raw.
3.  **`preprocess`**: Transforma los datos y genera la tabla transform.
4.  **`train`**: Entrena y exporta el modelo de inferencia.

<img width="1013" height="171" alt="image" src="https://github.com/user-attachments/assets/131f0c0f-50b5-44c8-b3b1-a3ddf5914043" />


## 3. Despliegue del Servidor de Inferencia (API)
Para consumir los modelos generados por el pipeline, se implementó una aplicación con **FastAPI** (`ServidorInferencia/api.py`).
*   **Despliegue:** Se configuró como un servicio (`app`) en el `docker-compose.yml`. Este servicio construye su imagen usando el archivo `ServidorInferencia/Dockerfile` (basado en `python:3.9`) y ejecuta la API usando `uvicorn`. Se expone hacia el host a través del puerto **8989**.
*   **Volumen de Modelos:** El contenedor de la API mapea la misma carpeta local `./dags/models` a su ruta interna `/app/models`. Esto permite que la API acceda de forma transparente a los modelos `.pkl` que el DAG de Airflow expulsa tras ser entrenados.
*   **Endpoints:**
    *   `GET /models`: Lista todos los modelos disponibles en la carpeta compartida.
    *   `POST /items/`: Recibe las características del pingüino y el nombre del modelo a utilizar (`item.modelo`). Carga el modelo indicado con `joblib` y devuelve la predicción.
      
<img width="306" height="146" alt="image" src="https://github.com/user-attachments/assets/6abec340-a4e6-4519-bc14-6d66606e7c74" />

<img width="1919" height="990" alt="image" src="https://github.com/user-attachments/assets/fe65d985-1892-43e0-99f2-07962a4b670b" />

## 4. Instalación y Despliegue de Airflow
Para poder instalar las librerías se creó una imagen aparte basada en apache/airflow:2.11.1. No se usó la 2.6.0 que tenía el archivo orginal debido a que la versión de python que esta contenía no era compatible con las librerías.

Había un problema con el script de inicialización de airflow que hacía que al momento de arrancar saliera este error

<img width="1280" height="518" alt="image" src="https://github.com/user-attachments/assets/b13d5dca-f9ac-4ebb-b259-db8eea738fc1" />

por lo tanto después de buscar en internet la opción que se planteaba era eliminar el condicional y colocar directamente la versión de airflow

<img width="647" height="192" alt="image" src="https://github.com/user-attachments/assets/40e75b54-d24e-4d5e-9553-d9604108e8af" />

Al usar uv se tuvo el problema de que airflow no reconocía las librerías. Si se usaba el usuario airflow salía un problema de permisos de escritura, por lo tanto se optó por crear el archivo requirements.txt y usar pip lo que permitió levantar el servicio sin ningún inconveniente.

Después de realizar los ajustes pertinentes del codigo desarrollado en el virtualenv vs docker se logró completar el dag y se generó el modelo para que el servidor de inferencia lo pudiera consumir

<img width="1280" height="682" alt="image" src="https://github.com/user-attachments/assets/e4f31270-5774-47dc-858f-f065a9e529a2" />

