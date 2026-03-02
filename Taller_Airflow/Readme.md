Para poder instalar las librerías se creó una imagen aparte basada en apache/airflow:2.11.1. No se usó la 2.6.0 que tenía el archivo orginal debido a que la versión de python que esta contenía no era compatible con las librerías.

Había un problema con el script de inicialización de airflow que hacía que al momento de arrancar saliera este error

<img width="1280" height="518" alt="image" src="https://github.com/user-attachments/assets/b13d5dca-f9ac-4ebb-b259-db8eea738fc1" />

por lo tanto después de buscar en internet la opción que se planteaba era eliminar el condicional y colocar directamente la versión de airflow

<img width="647" height="192" alt="image" src="https://github.com/user-attachments/assets/40e75b54-d24e-4d5e-9553-d9604108e8af" />

Al usar uv se tuvo el problema de que airflow no reconocía las librerías. Si se usaba el usuario airflow salía un problema de permisos de escritura, por lo tanto se optó por crear el archivo requirements.txt y usar pip lo que permitió levantar el servicio sin ningún inconveniente.

Después de realizar los ajustes pertinentes del codigo desarrollado en el virtualenv vs docker se logró completar el dag y se generó el modelo para que el servidor de inferencia lo pudiera consumir

<img width="1280" height="682" alt="image" src="https://github.com/user-attachments/assets/e4f31270-5774-47dc-858f-f065a9e529a2" />

