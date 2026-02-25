FROM ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.6.0}

# instalar uv
RUN pip install uv

# crear directorio de trabajo
WORKDIR /app

# Copia el directorio actual al directorio del contenedor
COPY . . 

# Se instalan las dependencias necesarias con uv
RUN uv sync