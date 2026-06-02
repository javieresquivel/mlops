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

## Kubernetes

Para el despliegue a kubernetes se usa la herramienta kompose para convertir el `docker-compose.yml` a manifiestos ejecutando el comando:

```kompose convert -f docker-compose.yml -o komposefiles/ --volumes hostPath``` 

Una vez creados los archivos se debe solucionar el problema de lo volumenes ya que por defecto Kompose crea hostpath que son rutas a la misma carpeta y que generan problemas por permisos de escritura. Por lo tanto agregamos un archivo denominado `pvc.yml` que contiene la definición de los volumenes que vamos a usar. Este problema sucede principalmente con las bases de datos.

<img width="1526" height="426" alt="image" src="https://github.com/user-attachments/assets/8bf5b68d-f689-4423-a2f4-7cf5ebe7f96a" />

Luego se tiene que reemplazar el hostpath por el nombre del volumen en los archivos de tipo deployment

<img width="571" height="153" alt="image" src="https://github.com/user-attachments/assets/9424afb7-9dcb-496c-8e09-d6437537a322" />

Para que funcione correctamente el CI / CD se debe adjuntar en los deployment con imagenes propias la siguiente etiqueta

```imagePullPolicy: Always```

De lo contrario al contruir los contenedores toma la imagen del caché y no la última en docker hub que es lo que nos interesa

Se debe tener en cuenta también que al cambiar a kubernetes el mapeo de los puertos funciona de forma distinta. Mientras que en docker si nos conectamos desde un contenedor a otro usamos el puerto base del servicio, por ejemplo a mysql nos conectamos al 3306 independientemente si en el archivo docker compose mapeamos ese ```4000:3006``` en kubernetes si se debe llamar al puerto que se mapeó en el servicio, por lo tanto al llamar a mysql desde otro contenedor tendríamos que conectarnos al puerto 4000.

## Despliegue con Argo

Dado que al migrar de compose a kubernetes no se especifica un namespace, se debe crear manualmente de lo contrario interfiere con argo. En este caso se creó el namespace ```final```

<img width="653" height="208" alt="image" src="https://github.com/user-attachments/assets/135db98e-d475-4de6-b317-28158e444113" />

y se colocó en cada uno de los manifiestos generados con kompose en la etiquea ```metadata```

<img width="756" height="389" alt="image" src="https://github.com/user-attachments/assets/728aa20c-a9b6-40df-8b44-5a5d2da59a26" />

Una vez hecho esto se procede con la instalación de argo siguiendo el tutorial descrito en https://github.com/CristianDiazAlvarez/MLOPS_PUJ/blob/main/Niveles/4/argo/Tutorial_ArgoCD_GitOps.md

Una vez se tiene acceso a la interfaz gráfica se procede a vincular el repositorio de github donde tenemos el proyecto final

<img width="3184" height="706" alt="image" src="https://github.com/user-attachments/assets/188ed459-f1bd-4815-a077-09cdc93f0911" />

Tan pronto se vincula el repositorio se procede a crear la aplicación donde lo más relevante es especificar el path donde se encuentran los manifiestos de kubernetes que para nuestro caso se encuentran en ```proyecto_final/komposefiles ```

<img width="1668" height="471" alt="image" src="https://github.com/user-attachments/assets/0d7e9f55-1bff-4058-8b92-eda21199ec15" />

Una vez creada la aplicación se procede a sincronizar el repositorio con lo que, si no hay errores, todo se pone en verde indicando que la operación se realizó correctamente

<img width="3194" height="1018" alt="image" src="https://github.com/user-attachments/assets/df41f7e8-fe7d-4638-829b-7f3c3817f7fb" />









   




