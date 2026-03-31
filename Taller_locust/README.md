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

### 2. Entrenamiento y Registro de Modelo
- **Experimento**: Ejecución del entrenamiento de un modelo de Machine Learning y su registro en MLflow.
- **Docker Hub**: Construcción y subida de la imagen del servidor de inferencia a Docker Hub (`javieresquivel1/mlops:inferencia`).

### 3. Despliegue del Servidor de Inferencia
- Despliegue del contenedor de la API utilizando la imagen de Docker Hub.
- Se configuró el acceso a los artefactos almacenados en MinIO y se integró con el servidor de MLflow.

### 4. Pruebas de Carga con Locust
- Se creó una red externa (`mlops-net`) para permitir la comunicación entre el despliegue del servidor y un servicio Locust en un `docker-compose` independiente.
- Se desplegó Locust y se ejecutaron pruebas de carga iniciales.

## Análisis y Resultados de Rendimiento

A lo largo del taller, se realizaron múltiples pruebas para encontrar la configuración óptima del servidor de inferencia:

### Hallazgos Iniciales
- **Límite de Usuarios**: Al probar con **10,000 usuarios**, la API comenzó a fallar.
- **File Descriptors (OFD)**: Se identificaron errores de "Open File Descriptors". Se solucionaron aumentando los `ulimits` (file descriptors) a **65,535** tanto para la aplicación como para Locust.

### Optimización de Recursos
Se realizaron pruebas iterativas limitando los recursos:

1. **Recursos Insuficientes**: Al limitar a **256M de RAM** y **0.25 CPU**, las solicitudes por segundo (**RPS**) cayeron a **0**, ya que el servidor no era capaz de responder.
2. **Mínimo Funcional**: Se determinó que los recursos mínimos necesarios para una sola instancia estable bajo carga son:
   - **Memoria**: 512M
   - **CPUs**: 4.0

### Replicas
- Al implementar **3 réplicas**, la cantidad de RPS aumentó significativamente.
- Se descubrió que al aumentar el número de réplicas, era posible disminuir los recursos individuales de cada una.

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

