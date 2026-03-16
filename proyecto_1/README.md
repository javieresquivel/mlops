# Proyecto 1 MINIO

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano

# MINIO
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
