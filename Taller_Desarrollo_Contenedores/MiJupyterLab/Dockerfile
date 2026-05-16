FROM python:3.9

# instalar uv
RUN pip install uv

# crear directorio de trabajo
WORKDIR /app

# Copia el directorio actual al directorio del contenedor
COPY . . 

# Se instalan las dependencias necesarias con uv
RUN uv sync

# iniciar jupyterlab usando uv
CMD ["uv", "run", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token="]
