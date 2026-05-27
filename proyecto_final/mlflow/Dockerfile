# Imagen base ligera con Python
FROM python:3.9-slim

# Variables de entorno necesarias para MLflow con S3/MinIO
# ENV MLFLOW_S3_ENDPOINT_URL=http://10.43.100.99:8000 \
#     AWS_ACCESS_KEY_ID=admin \
#     AWS_SECRET_ACCESS_KEY=supersecret \
#     BACKEND_STORE_URI=sqlite:///mlflow.db \
#     ARTIFACT_ROOT=s3://mlflows/artifacts

# Instalar MLflow
RUN pip install --no-cache-dir mlflow boto3 pymysql cryptography

# Crear directorio de trabajo
WORKDIR /app

# Exponer el puerto del servidor MLflow
EXPOSE 8003

# Comando por defecto
CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "8003", \
     "--backend-store-uri", "mysql+pymysql://user:password@mysql:3306/mlflow_db", \
     "--default-artifact-root", "s3://mlflows/artifacts", \
     "--serve-artifacts"]