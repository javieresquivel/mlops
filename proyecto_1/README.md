# Proyecto 1 MINIO

## Desarrollado por: **Grupo 9**
- Javier Esquivel
- Santiago Serrano

---

## Arquitectura y Flujo de Trabajo

### 1. Orquestación con Airflow (DAG)
Se ha implementado un DAG en Airflow que se ejecuta automáticamente cada **5 minutos**. Este DAG es el encargado de disparar la recolección de datos llamando a la función principal que realiza la captura de datos.

  <img width="389" height="422" alt="image" src="https://github.com/user-attachments/assets/3d7d748c-5c33-49d4-a79b-d131325e849d" />

### 2. Consulta del API y Escritura en Base de Datos
- **Ingesta Incremental**: Se creó un método que consulta el API externo utilizando el ID del grupo (Grupo 9).
  
  <img width="921" height="278" alt="image" src="https://github.com/user-attachments/assets/5a050038-0cc6-48f5-9536-232fd7432a2f" />
  
- **Almacenamiento**: Los datos recibidos son procesados y almacenados en una base de datos MySQL, específicamente en la tabla `raw`, de manera incremental.
  
  <img width="548" height="716" alt="image" src="https://github.com/user-attachments/assets/b27bc73a-e26b-42e1-ae20-1bcb83f67782" />
  
- **Control de Ciclos**: Se implementó un condicional que detecta cuando se llega al **batch 9**; en este punto, el sistema envía una señal al API para reiniciar el contador de generación de datos.
  
  <img width="921" height="486" alt="image" src="https://github.com/user-attachments/assets/b95feb9d-4122-464a-9662-41c0ea3136b3" />

### 3. Procesamiento en Jupyter y Entrenamiento
Desde un libro de **Jupyter Lab** corriendo en un contenedor:
1. **Lectura de BBDD**: Se extraen los datos de la tabla `raw` de MySQL.
2. **Transformación**: Se aplican procesos de limpieza, encoding y preprocesamiento de los datos.
   <img width="597" height="231" alt="image" src="https://github.com/user-attachments/assets/9799a84f-7584-4b67-85a2-569f34843d44" />
4. **Persistencia**: Los datos transformados se guardan nuevamente en la base de datos, en la tabla `transformed`.
5. **Entrenamiento**: Se entrena un modelo de clasificación utilizando los datos preparados.
   <img width="769" height="481" alt="image" src="https://github.com/user-attachments/assets/c38a068e-2961-4efa-89fd-fcb905054e2f" />
   <img width="921" height="490" alt="image" src="https://github.com/user-attachments/assets/d6cb4a4e-bd7f-4063-bea4-aec9aa6d20e3" /> 
7. **Registro en Minio**: El modelo final entrenado se exporta y se guarda automáticamente en el servicio de almacenamiento de objetos **Minio** para su posterior despliegue.
  <img width="921" height="232" alt="image" src="https://github.com/user-attachments/assets/d70be3d8-a3a7-42a8-a7ff-c05c90ba244e" />

### 4. Servidor de Inferencia
El servidor de inferencia basado en FastAPI permite el consumo del modelo:
- **Consulta en Minio**: El API detecta y lista los modelos disponibles directamente desde el bucket de Minio.
  <img width="921" height="175" alt="image" src="https://github.com/user-attachments/assets/d58d1c5e-44c2-429d-9e01-69df71d6e90a" />
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
