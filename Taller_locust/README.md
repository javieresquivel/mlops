# Taller MLOps: Taller Locust

## Desarrollado por

**Grupo 9**
- Javier Esquivel
- Santiago Serrano

## Pasos de Implementación

### 1. Configuración de Infraestructura
- **Docker Compose**: Creación de un entorno contenedorizado con servicios los siguientes servicios: PostgreSQL, MinIO, MLflow y Jupyter.
- **Inicio de Servicios**: Despliegue de los servicios iniciales.
- **MinIO**: Creación del bucket `experimentos` para el almacenamiento de artefactos.
   <img width="921" height="299" alt="image" src="https://github.com/user-attachments/assets/9ed2ecfd-79bd-41dc-87eb-a01376c878e0" />

### 2. Entrenamiento y Registro de Modelo
- **Experimento**: Ejecución del entrenamiento de un modelo de Machine Learning y su registro en MLflow.
  <img width="921" height="137" alt="image" src="https://github.com/user-attachments/assets/93a28b32-514b-4344-954a-c33d74c1cf4e" />

### 3. Despliegue del Servidor de Inferencia
- **Docker Hub**: Construcción y subida de la imagen del servidor de inferencia a Docker Hub (`javieresquivel1/mlops:inferencia`).
  <img width="1900" height="976" alt="image" src="https://github.com/user-attachments/assets/4a39c15e-b282-4eca-8b0c-3c02a4f5228f" />
- Despliegue del contenedor de la API utilizando la imagen de Docker Hub.
- Se configuró el acceso a los artefactos almacenados en MinIO y se integró con el servidor de MLflow.

### 4. Pruebas de Carga con Locust
- Se creó una red externa (`mlops-net`) para permitir la comunicación entre el despliegue del servidor y un servicio Locust en un `docker-compose` independiente.
- Se desplegó Locust y se ejecutaron pruebas de carga iniciales.
   <img width="921" height="578" alt="image" src="https://github.com/user-attachments/assets/6fd9826c-27fb-49dc-8ff3-4aaab4021cae" />

## Análisis y Resultados de Rendimiento

A lo largo del taller, se realizaron múltiples pruebas para encontrar la configuración óptima del servidor de inferencia:

### Hallazgos Iniciales
- **Límite de Usuarios**: Al probar con **10,000 usuarios**, la API comenzó a fallar.
  <img width="921" height="630" alt="image" src="https://github.com/user-attachments/assets/c7dd6e31-2226-4de2-abbf-577ee847f17d" />
- **File Descriptors (OFD)**: Se identificaron errores de "Open File Descriptors". Se solucionaron aumentando los `ulimits` (file descriptors) a **65,535** tanto para la aplicación como para Locust.
   <img width="921" height="611" alt="image" src="https://github.com/user-attachments/assets/d51e78c9-5119-4ce3-a621-202994684f90" />

### Optimización de Recursos
Se realizaron pruebas iterativas limitando los recursos:

1. **Recursos Insuficientes**: Al limitar a **256M de RAM** y **0.25 CPU**, las solicitudes por segundo (**RPS**) cayeron a **0**, ya que el servidor no era capaz de responder.
   <img width="921" height="538" alt="image" src="https://github.com/user-attachments/assets/569be24f-2b39-4852-be30-752c6ccbc3a1" />

3. **Mínimo Funcional**: Se determinó que los recursos mínimos necesarios para una sola instancia estable bajo carga son:
   - **Memoria**: 512M
   - **CPUs**: 4.0
   <img width="921" height="595" alt="image" src="https://github.com/user-attachments/assets/45ba731e-03e7-4a6e-87a9-f11fc9b1d6bd" />

### Replicas
- Al implementar **3 réplicas**, la cantidad de RPS aumentó significativamente.
   <img width="921" height="111" alt="image" src="https://github.com/user-attachments/assets/48f79e01-e4fb-47a1-b06a-46c4cfae3f32" />
   <img width="921" height="576" alt="image" src="https://github.com/user-attachments/assets/759a5e3b-16d1-4a74-a6d3-1fa5c4759381" />

- Se descubrió que al aumentar el número de réplicas, era posible disminuir los recursos individuales de cada una.
   <img width="921" height="569" alt="image" src="https://github.com/user-attachments/assets/e3ca7e90-9021-422e-b86f-c11727436478" />

## Configuración Óptima Encontrada

Tras multiples pruebas, la mejor configuración para maximizar el rendimiento fue:

- **Cantidad de Réplicas**: 4
- **Memoria por Réplica**: 256M
- **CPU por Réplica**: 4.0

```yaml
deploy:
  replicas: 4
  resources:
    limits:
      memory: 256M
      cpus: 4.0
```

<img width="921" height="603" alt="image" src="https://github.com/user-attachments/assets/864bbf98-1715-4ada-b033-65ec6fbe6fc4" />
