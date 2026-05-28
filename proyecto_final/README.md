Finalmente se debe configurar el archivo ``` .github/workflows/docker-publish.yml ``` que contiene las instrucciones necesarias para recorrer las carpetas que tienen un Dockerfile y que vamos a publicar

## Desarrollado por: **Grupo 9**
- Javier Esquivel
- Santiago Serrano

## Descripcion General

Este proyecto implementa una arquitectura completa de MLOps para resolver un problema de regresion de precios de propiedades inmobiliarias. El dataset cuenta con 12 variables como numero de habitaciones, banos, tamano del terreno, ubicacion y fecha de venta previa, entre otras. Los datos se reciben por lotes desde una API externa y pasan por un pipeline de ingesta, validacion, preprocesamiento y entrenamiento orquestado por Apache Airflow. El modelo resultante se despliega en una API FastAPI con capacidad de recarga en caliente, y todo el sistema es monitoreable via Prometheus y Grafana.

## DAG — mlops_ingestion_pipeline (18 tareas)

El DAG se ejecuta manualmente y cada corrida procesa un lote de datos. Las primeras 7 tareas se encargan de obtener los datos desde la API externa, validar su esquema y calidad, detectar nuevas categorias y drift, y preprocesarlos para dejarlos listos para entrenamiento. La tarea 8 decide si vale la pena entrenar segun reglas tecnicas como volumen minimo, presencia de drift o categorias nuevas. Si se decide entrenar, las tareas 9 a 14 construyen un pipeline de RandomForest con busqueda de hiperparametros, lo evaluan, lo registran en MLflow, lo comparan contra el modelo en produccion y, si cumple los criterios de mejora, lo promueven. Finalmente, las tareas 15 a 18 registran el resultado en una tabla de historial y cierran la ejecucion.

| # | Tarea | Que hace |
|---|-------|----------|
| 1 | `start` | Log de inicio |
| 2 | `fetch_batch_from_api` | Consulta `data-api:80/data?group_number=N`. Inserta en `raw_data` con `batch_group` y `ingested_at`. Registra metadatos en `batch_log`. HTTP 400 (datos agotados) → dropea `raw_data`, `clean_data`, `batch_log` y reinicia data-api |
| 3 | `validate_schema` | Verifica 12 columnas y tipos correctos |
| 4 | `validate_data_quality` | Nulos criticos, duplicados, rangos, consistencia banos/cuartos, status validos |
| 5 | `detect_new_categories` | Compara `status`, `city`, `state`, `prev_sold_date` contra `known_categories`. Registra nuevas |
| 6 | `detect_data_drift` | PSI por variable vs historico de `raw_data`. Threshold 0.1 |
| 7 | `preprocess_data` | Imputa nulos, crea `price_per_sqft`, `room_total`, `has_prev_sold`. Persiste en `clean_data` |
| 8 | `decide_training` | Reglas en orden: sin modelo prod (entrena), drift (entrena), categorias nuevas (entrena), volumen < 100 o calidad mala (salta), default (salta) |
| 9 | `train_model` | Pipeline: ColumnTransformer (StandardScaler + OHE) + GridSearchCV(RandomForest). Guarda en `/tmp/` |
| 10 | `evaluate_model` | 80/20. MAE, MSE, RMSE, R2. Graficos de importancia y residuales |
| 11 | `register_model` | MLflow: parametros, metricas, artefactos (graficos, dataset), firma. Registra como `real-estate-model` |
| 12 | `compare_with_production` | Compara candidato vs alias `prod`. Si es el primero o MAE >= 3% mejor y RMSE <= 1% peor, promueve |
| 13 | `decide_promotion` | Bifurca a `promote_model` o `reject_model` |
| 14 | `promote_model` | Asigna alias `prod` en MLflow + `POST /model` al API |
| 15 | `reject_model` | Log de rechazo |
| 16 | `skip_training` | Log de salto |
| 17 | `notify_or_log_result` | Inserta en `training_history` (decision, metricas, version, razon) |
| 18 | `end` | Log de finalizacion |

### Tablas en MySQL (`training`)

La base de datos de entrenamiento cuenta con 6 tablas que organizan los datos en distintas capas segun su nivel de procesamiento. `raw_data` almacena los registros tal como llegan de la API, con un identificador de lote y marca de tiempo. `clean_data` contiene los datos ya imputados y con variables derivadas como precio por metro cuadrado. `known_categories` lleva un historico de todos los valores categoricos que han aparecido para detectar nuevos. `batch_log` registra metadatos de cada lote recibido. `training_history` guarda el resultado de cada ejecucion del DAG (si entreno, si se promovio, metricas). `inference_logs` almacena cada prediccion realizada por la API con su entrada, resultado y latencia.

| Tabla | Uso |
|-------|-----|
| `raw_data` | Datos crudos por lote con `batch_group` e `ingested_at` |
| `clean_data` | Datos preprocesados con `price_per_sqft`, `room_total`, `has_prev_sold` |
| `known_categories` | Historial de valores categoricos vistos |
| `batch_log` | Metadatos de cada lote (`group_number`, `batch_size`, `inserted_rows`) |
| `training_history` | Resultado de cada ejecucion del DAG |
| `inference_logs` | Log de predicciones del API |

## MLflow

Cada entrenamiento registra en MLflow los parametros del modelo (n_estimators, max_depth, min_samples_split), las metricas de test y train (MAE, MSE, RMSE, R2), y artefactos como el pipeline serializado, grafico de importancia de variables, grafico de residuales y el dataset usado. El backend es MySQL y los artefactos se almacenan en MinIO. Cuando un modelo candidato supera al productivo segun las reglas RF6, se actualiza el alias `prod` en el registry de MLflow para que apunte a la nueva version.

## API FastAPI

La API de inferencia expone 5 endpoints. El principal es `POST /predict`, que recibe los 11 campos de una propiedad (todo excepto el precio), completa valores faltantes, calcula las variables derivadas y ejecuta la prediccion con el pipeline de RandomForest. El modelo se mantiene en memoria cache para responder en milisegundos, y puede recargarse sin reiniciar el contenedor mediante `POST /model`, que lo descarga desde MLflow, lo guarda a disco y actualiza la cache. Cada prediccion se guarda de forma asincrona en la tabla `inference_logs` para no bloquear la respuesta.

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/predict` | POST | Recibe 11 campos, hace feature engineering, predice precio |
| `/model` | POST | Recarga modelo desde MLflow en memoria y disco |
| `/model-info` | GET | Nombre, alias, version, run_id, estado |
| `/health` | GET | Health check |
| `/metrics` | GET | Metricas Prometheus |

## Monitoreo

La API expone metricas de Prometheus en `/metrics`: contador de requests exitosos y fallidos, histograma de latencia, y distribucion de predicciones. Grafana consume estas metricas en un dashboard pre-configurado. Para pruebas de carga, Locust puede lanzar 50 o mas usuarios concurrentes contra el endpoint de prediccion para validar el comportamiento bajo estres.

## Implementación de Github actions
Dado que las imagenes a construir se van a publicar en Dockerhub lo primero que se tiene que hacer es genear un `Personal access token` en Dockerhub

<img width="433" height="1188" alt="image" src="https://github.com/user-attachments/assets/91fd9731-d8a4-4b1d-be5b-dcded6ab229b" />

Posteriormente se deben configurar las variables de secretos en el repositorio de github para que este tenga las credenciales para realizar la publicación

<img width="2128" height="1189" alt="Captura desde 2026-05-27 09-35-25" src="https://github.com/user-attachments/assets/8cf6e6c6-9312-4abe-88eb-5f12625df6af" />
