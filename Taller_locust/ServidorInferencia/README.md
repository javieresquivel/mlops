Se creó la configuración del servidor creando el docker file desde el directorio que contiene el archivo pkl del modelo y el .py del servidor

luego se construye la imagen usando el comando: docker build -t taller1:1 .

Posteriormente se ejcuta el comando docker run --name taller1 -p 8989:80 taller1:1 (Izquierda host, derecha contenedor) que inicia el servicio y en la consola aparece la siguiente imagen:

<img width="862" height="227" alt="image" src="https://github.com/user-attachments/assets/a9e4dcab-3b8f-463d-8a06-7551ab1a5f1d" />

Luego se usa el link /docs para probar el api

<img width="1142" height="544" alt="image" src="https://github.com/user-attachments/assets/6269b857-61a9-4954-a2c3-c1f6027e7659" />

Se usan los siguientes datos de prueba que corresponden al primer registro del archivo csv

{
  "island": 1,
  "bill_length_mm": 39.1,
  "bill_depth_mm": 18.7,
  "flipper_length_mm": 181,
  "body_mass_g": 3750,
  "sex": 1
}

Finalmente se le da execute y se obtiene el resultado con código 200 lo que indica que la operación se ejecutó correctamente:

<img width="1069" height="466" alt="image" src="https://github.com/user-attachments/assets/f536ec1d-3c7e-482a-8ac8-d6e77324fda2" />


