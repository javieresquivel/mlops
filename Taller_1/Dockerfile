FROM python:3.9
# Copia el directorio actual al directorio del contenedor
COPY . . 
# Se instalan las dependencias necesarias
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt
# Se corre el servidor uvicorn en el puerto 80 para que se pueda acceder desde el navegador
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "80"]