
FROM ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.6.0}

# instalar uv
RUN apt-get update && \
	apt-get install -y build-essential libffi-dev && \
	pip install --upgrade pip && \
	pip install uv

# crear directorio de trabajo
WORKDIR /app

# Copia el directorio actual al directorio del contenedor
COPY . . 

# Se instalan las dependencias necesarias con uv
RUN uv sync