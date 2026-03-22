# Imagen base ligera con Python
FROM python:3.9-slim

# Variables de entorno necesarias para MLflow con S3/MinIO
ENV MLFLOW_S3_ENDPOINT_URL=http://minio:9000 \
    AWS_ACCESS_KEY_ID=admin \
    AWS_SECRET_ACCESS_KEY=supersecret \
    #BACKEND_STORE_URI=postgresql://mlflow:mlflow@postgres:5432/mlflow \
    ARTIFACT_ROOT=s3://mlflows3/artifacts

# Instalar MLflow
#RUN pip install --no-cache-dir mlflow boto3 psycopg2-binary
RUN pip install mlflow boto3 psycopg2-binary

# Crear directorio de trabajo
WORKDIR /app

# Exponer el puerto del servidor MLflow
EXPOSE 5000

# Comando por defecto
CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "5000", \
     "--backend-store-uri", "postgresql://mlflow:mlflow@postgres:5432/mlflow", \
     "--default-artifact-root", "s3://mlflows3/artifacts", \
     "--serve-artifacts"]
