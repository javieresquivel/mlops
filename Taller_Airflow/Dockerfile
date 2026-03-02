# Definimos la imagen base
ARG AIRFLOW_IMAGE_NAME=apache/airflow:2.11.1
FROM ${AIRFLOW_IMAGE_NAME}

# Cambiamos a root para instalar dependencias del sistema
USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Forzamos la actualización de pip e instalamos uv
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir uv

# Establecemos el directorio de trabajo (Airflow usa /opt/airflow por defecto)
WORKDIR /opt/airflow

USER airflow

# Copiamos los archivos de dependencias primero (mejora la caché de Docker)
COPY --chown=airflow:0 pyproject.toml uv.lock* ./
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install apache-airflow==${AIRFLOW_VERSION}


# Instalamos las dependencias. 
# Nota: Airflow ya tiene un entorno virtual, uv pip install suele ser más directo
#RUN if [ -f pyproject.toml ]; then \
#    uv pip install --no-cache-dir --system -r pyproject.toml; \
#    fi