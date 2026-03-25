# MLFLOW

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano

## 1. Despliegue de servicios
Para el despliegue de la solución se utilizó **Docker Compose**, integrando los siguientes servicios:

*   **PostgreSQL (Metadata MLflow):** Se implementó una base de datos PostgreSQL para actuar como el *backend store* de MLflow, permitiendo persistir toda la metadata de los experimentos.
*   **PostgreSQL (Dataset):** Se configuró un segundo servicio de base de datos llamado `postgres_train` destinado exclusivamente al almacenamiento del dataset de pingüinos para el proceso de entrenamiento.
*   **MinIO (Artifact Store):** Se desplegó un servidor de almacenamiento compatible con S3 para gestionar los artefactos de los modelos.
*   **Jupyter:** Se configuró un contenedor con Jupyter Lab para la limpieza de datos, el análisis exploratorio y la ejecución de los scripts de entrenamiento que interactúan con MLflow.
*   **MLflow Server:** Gestiona el registro de experimentos y almacenamiento de modelos, conectado a la base de datos PostgreSQL y al almacenamiento MinIO. Se agregó `depends_on` para que se iniciara después de la base de datos `postgres` y MinIO.
*   **Servidor de Inferencia (FastAPI):** Servicio que consume el modelo disponible en MLFLOW.

## 2. Creación del bucket
Para que MLFLOW pudiera almacenar los datos se creó el bucket `mlflow3`

<img width="508" height="338" alt="image" src="https://github.com/user-attachments/assets/7dbc9e34-8157-43d0-b7d5-ac3d50fc2c5b" />

## 3. Ejecución del entrenamiento
Primero se limpió el dataset y luego se realizó el entrenamiento ejecutando 20 experimentos utilizando un modelo de Random Forest para clasificar las especies de pingüinos. En cada una de estas 20 iteraciones, el script varió de forma aleatoria tres hiperparámetros críticos: el número de árboles (n_estimators), la profundidad máxima de cada árbol (max_depth) y el número mínimo de muestras necesarias para dividir un nodo (min_samples_split).
Las métricas se iban enviando a MLFLOW

<img width="1069" height="553" alt="image" src="https://github.com/user-attachments/assets/e453250c-e0a3-4275-87e5-f0858ffc35d3" />

## 4. Revisión de los experimentos en MLFLOW
Al ingresar a MLFLOW se encontraron las 20 ejecuciones realizadas

<img width="1443" height="778" alt="image" src="https://github.com/user-attachments/assets/e6038702-62c6-48be-be68-9c04d3361a6a" />

Al entrar a revisar los registros se tienen cargados los modelos en MINIO

<img width="1156" height="515" alt="image" src="https://github.com/user-attachments/assets/27fa1ddc-1fbe-4ee9-afb8-fa1452c389c2" />

## 5. Registro de ambientes de mlflow

Se creó un ambiente de producción para enviar el que mejor resultado tuviera y que es el que va a usar el servidor de inferencia

<img width="1605" height="408" alt="image" src="https://github.com/user-attachments/assets/23de4b7c-8272-40d8-9cd9-4825586ef6d3" />

## 6. Consulta del modelo en producción a través de MLFLOW

Por último se hizo la petición a MLFLOW desde FASTAPI estableciendo las variables de entorno para que internamente se pudiera conectar
<img width="632" height="209" alt="image" src="https://github.com/user-attachments/assets/a620ecfe-78fc-43c4-a48d-fae2c66354b6" />

Luego se carga el modelo de producción al arrancar el servidor de FASTAPI lo que permite realizar la inferencia

<img width="1604" height="715" alt="image" src="https://github.com/user-attachments/assets/9c9f03e6-b661-4894-9a70-3f12bbfcda92" />





