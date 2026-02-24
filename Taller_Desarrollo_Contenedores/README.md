# Compartir datos entre contenedores mediante volumenes

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano
  
## Servidor de entrenamiento (Jupyterlab)

El servidor de entrenamiento está basado en JupyterLab y se encuentra en la carpeta `ServidorJupiter/MiJupyterLab`. Este contenedor permite preparar, entrenar y guardar modelos random forest usando el dataset Penguins.

### Estructura
- **Dockerfile**: Define la imagen basada en Python 3.9, instala dependencias con `uv` y ejecuta JupyterLab.
- **pyproject.toml**: Lista las dependencias principales: `jupyterlab`, `matplotlib`, `pandas`, `scikit-learn` y `seaborn`.
- **train.ipynb**: Notebook base para entrenamiento de modelos usando el dataset `penguins.csv`.
- **Data/**: Carpeta con csv del dataset `penguins.csv`.

### Volúmenes
En el archivo `docker-compose.yaml` se configuran los volúmenes:
- `../models:/app/models`: Permite guardar los modelos entrenados en una carpeta compartida accesible por otros contenedores.
- `./Data:/app/Data`: Permite acceder a los datos de entrenamiento.

### Uso
1. Construir y levantar el contenedor:
	```bash
	docker-compose up --build
	```
2. Acceder a JupyterLab en [localhost:8888](http://localhost:8888).

  <img width="1919" height="986" alt="image" src="https://github.com/user-attachments/assets/8a2c7e58-545c-4102-8709-39e7766594ed" />

3. Utilizar el notebook `train.ipynb` para entrenar modelos y guardarlos en `/app/models`.

  <img width="509" height="285" alt="image" src="https://github.com/user-attachments/assets/225dc403-7683-4892-8704-b4750b452b7c" />

Esto permite que los modelos generados estén disponibles para el servidor de inferencia, facilitando el flujo de trabajo entre entrenamiento e inferencia.

## Servidor de inferencia

Para este servidor se creó el archivo de docker-compose.yml que tenía el volumen ../models:/app/models, de igual forma se dejó para el servidor de entrenamiento. De esta forma ambos conenedores tendrían acceso al mismo espacio de almacenamiento.

Luego se usó una función para listar los archivos dentro del folder /app/models y se creó una url tipo GET /models para que se pudieran consultar los modelos disponibles y así el usuario pudiera elegir cual utilizar para realizar la predicción

<img width="1121" height="578" alt="image" src="https://github.com/user-attachments/assets/bcbe9642-7e8a-4498-aa4e-7b2e9e79a654" />

De esta forma solo se agrega el parámetro del modelo al realizar la petición

<img width="1130" height="551" alt="image" src="https://github.com/user-attachments/assets/f45283a0-fc8d-4f68-be57-cfcd1456de0b" />

<img width="1101" height="300" alt="image" src="https://github.com/user-attachments/assets/1635b7d3-e561-46bb-9ba5-982ff59da9aa" />

Finalmente se hace un control en el api para que si el modelo seleccionado no existe se genere un 404.

