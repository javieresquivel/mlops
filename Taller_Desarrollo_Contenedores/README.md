# Compartir datos entre contenedores mediante volumenes

## Servidor de entrenamiento (Jupiterlab)

## Servidor de inferencia

Para este servidor se creó el archivo de docker-compose.yml que tenía el volumen ../models:/app/models, de igual forma se dejó para el servidor de entrenamiento. De esta forma ambos conenedores tendrían acceso al mismo espacio de almacenamiento.

Luego se usó una función para listar los archivos dentro del folder /app/models y se creó una url tipo GET /models para que se pudieran consultar los modelos disponibles y así el usuario pudiera elegir cual utilizar para realizar la predicción