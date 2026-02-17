# Clasificador de Especies de Pingüinos

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano

## Desarrollo

### 1. Entrenamiento del Modelo

Se entrenó el modelo usando Random Forest siguiendo las etapas de procesamiento de datos y creación del modelo. El detalle del entrenamiento está documentado en el archivo [train.ipynb](train.ipynb).

### 2. API con FastAPI

Se creó un API con FastAPI y se creó el endpoint `/items` que recibe los features de entrada y devuelve la predicción del modelo previamente entrenado. El detalle del API está documentado en el archivo [api.py](api.py).

### 3. Configuración del Servidor con Docker

Se creó la configuración del servidor creando el docker file desde el directorio que contiene el archivo pkl del modelo y el .py del servidor, los detalles del DockerFile los encuentra en [Dockerfile](Dockerfile)

luego se construye la imagen usando el comando:

```bash
docker build -t taller1:1 .
```

Posteriormente se ejecuta el comando que inicia el servicio

```bash
docker run --name taller1 -p 8989:80 taller1:1
```
*(Izquierda: puerto del host, derecha: puerto del contenedor)*

Al iniciar el servicio, en la consola aparece la siguiente imagen:

<img width="862" height="227" alt="image" src="https://github.com/user-attachments/assets/a9e4dcab-3b8f-463d-8a06-7551ab1a5f1d" />


Luego se usa el link [`/docs`](http://localhost:8989/docs) para probar el API

<img width="1142" height="544" alt="image" src="https://github.com/user-attachments/assets/6269b857-61a9-4954-a2c3-c1f6027e7659" />

**Datos de prueba utilizados**:
Se usan los siguientes datos de prueba que corresponden al primer registro del archivo csv

```json
{
  "island": 1,
  "bill_length_mm": 39.1,
  "bill_depth_mm": 18.7,
  "flipper_length_mm": 181,
  "body_mass_g": 3750,
  "sex": 1
}
```

**Resultado de la predicción:**

Finalmente se le da execute y se obtiene el resultado con código 200 lo que indica que la operación se ejecutó correctamente:

<img width="1069" height="466" alt="image" src="https://github.com/user-attachments/assets/f536ec1d-3c7e-482a-8ac8-d6e77324fda2" />


