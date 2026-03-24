# MLFLOW

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano

## 1. Despliegue de servicios
Se configuró el YML para montar todos los servicios requeridos adicionando un servicio BD llamado postgres_train para almacenar los datos del dataset penguins para entrenar el modelo

## 2. Creación del bucker
Para que MLFLOW pudiera almacenar los datos se creó el bucket mlflow3

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


