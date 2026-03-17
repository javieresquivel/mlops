# Proyecto 1 MINIO

## Desarrollado por: **Grupo 9**
- Javier Esquivel
- Santiago Serrano

---

## Arquitectura y Flujo de Trabajo

### 1. Orquestación con Airflow (DAG)
Se ha implementado un DAG en Airflow que se ejecuta automáticamente cada **5 minutos**. Este DAG es el encargado de disparar la recolección de datos llamando a la función principal que realiza la captura de datos.

### 2. Consulta del API y Escritura en Base de Datos
- **Ingesta Incremental**: Se creó un método que consulta el API externo utilizando el ID del grupo (Grupo 9). 
- **Almacenamiento**: Los datos recibidos son procesados y almacenados en una base de datos MySQL, específicamente en la tabla `raw`, de manera incremental.
- **Control de Ciclos**: Se implementó un condicional que detecta cuando se llega al **batch 9**; en este punto, el sistema envía una señal al API para reiniciar el contador de generación de datos.

### 3. Procesamiento en Jupyter y Entrenamiento
Desde un libro de **Jupyter Lab** corriendo en un contenedor:
1. **Lectura de BBDD**: Se extraen los datos de la tabla `raw` de MySQL.
2. **Transformación**: Se aplican procesos de limpieza, encoding y preprocesamiento de los datos.
3. **Persistencia**: Los datos transformados se guardan nuevamente en la base de datos, en la tabla `transformed`.
4. **Entrenamiento**: Se entrena un modelo de clasificación utilizando los datos preparados.
5. **Registro en Minio**: El modelo final entrenado se exporta y se guarda automáticamente en el servicio de almacenamiento de objetos **Minio** para su posterior despliegue.

### 4. Servidor de Inferencia
El servidor de inferencia basado en FastAPI permite el consumo del modelo:
- **Consulta en Minio**: El API detecta y lista los modelos disponibles directamente desde el bucket de Minio.
- **Predicciones en Tiempo Real**: Se utilizan estos modelos cargados dinámicamente para realizar inferencias basadas en las características del dataset Covertype.

---

## Servicios Integrados

### MINIO
Para la integración con este servicio se parte de la base del taller de Airflow y se agrega el servicio en el yml y realizamos el docker-compose up para validar que esté sirviendo. Al ingresar al navegador por el puerto configurado nos arroja la ventana de inicio

<img width="1917" height="675" alt="image" src="https://github.com/user-attachments/assets/003f540b-5187-4617-85e8-54772235028a" />

Una vez ingresamos con las credenciales del yml se procede a crear el bucket **modelos** donde se alojará la información

<img width="1910" height="399" alt="image" src="https://github.com/user-attachments/assets/8121c817-3c02-44d4-8c8c-a7042d2f040d" />

Para usarlo se modifica el servidor de inferencia modificando el método de consultar modelos que antes apuntaba a un volumen para que ahora haga la petición al servicio **minio** usando la librería boto3 y así obtener los modelos disponibles para usar.

<img width="919" height="407" alt="image" src="https://github.com/user-attachments/assets/4009e526-88be-43ef-b96b-ba0e41525597" />

Se dejan variables por defecto pero también se da la posibilidad de colocar los valores desde el yml.
Al hacer la prueba ya se logran obtener los objetos de minio

<img width="1427" height="508" alt="image" src="https://github.com/user-attachments/assets/ff5ef6dd-1be0-431b-b2c6-050396701cff" />

<img width="750" height="414" alt="image" src="https://github.com/user-attachments/assets/aa8adfcf-23ec-4d7d-8973-d13e747c9fef" />
