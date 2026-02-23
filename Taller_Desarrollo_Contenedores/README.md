# Compartir datos entre contenedores mediante volumenes

## Servidor de entrenamiento (Jupiterlab)

## Servidor de inferencia

Para este servidor se creó el archivo de docker-compose.yml que tenía el volumen ../models:/app/models, de igual forma se dejó para el servidor de entrenamiento. De esta forma ambos conenedores tendrían acceso al mismo espacio de almacenamiento.

Luego se usó una función para listar los archivos dentro del folder /app/models y se creó una url tipo GET /models para que se pudieran consultar los modelos disponibles y así el usuario pudiera elegir cual utilizar para realizar la predicción

<img width="1121" height="578" alt="image" src="https://github.com/user-attachments/assets/bcbe9642-7e8a-4498-aa4e-7b2e9e79a654" />

De esta forma solo se agrega el parámetro del modelo al realizar la petición

<img width="1130" height="551" alt="image" src="https://github.com/user-attachments/assets/f45283a0-fc8d-4f68-be57-cfcd1456de0b" />

<img width="1101" height="300" alt="image" src="https://github.com/user-attachments/assets/1635b7d3-e561-46bb-9ba5-982ff59da9aa" />

Finalmente se hace un control en el api para que si el modelo seleccionado no existe se genere un 404.

