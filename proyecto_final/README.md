## Implementación de Github actions
Dado que las imagenes a construir se van a publicar en Dockerhub lo primero que se tiene que hacer es genear un `Personal access token` en Dockerhub

<img width="433" height="1188" alt="image" src="https://github.com/user-attachments/assets/91fd9731-d8a4-4b1d-be5b-dcded6ab229b" />

Posteriormente se deben configurar las variables de secretos en el repositorio de github para que este tenga las credenciales para realizar la publicación

<img width="2128" height="1189" alt="Captura desde 2026-05-27 09-35-25" src="https://github.com/user-attachments/assets/8cf6e6c6-9312-4abe-88eb-5f12625df6af" />

Finalmente se debe configurar el archivo ``` .github/workflows/docker-publish.yml ``` que contiene las instrucciones necesarias para recorrer las carpetas que tienen un Dockerfile y que vamos a publicar 
