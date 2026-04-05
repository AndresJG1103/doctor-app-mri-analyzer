# Configuración CPU/GPU

Esta guía explica cómo configurar el procesamiento MRI usando CPU o GPU (NVIDIA).

## Índice

- [Modo CPU](#modo-cpu)
- [Modo GPU](#modo-gpu)
- [Selección de GPU específica](#selección-de-gpu-específica)
- [Troubleshooting](#troubleshooting)
- [Tiempos de procesamiento](#tiempos-de-procesamiento)

---

## Modo CPU

El modo CPU es la configuración por defecto y no requiere hardware especial.

### Configuración

En el archivo `.env`:

```bash
FASTSURFER_USE_GPU=false
FASTSURFER_DEVICE=cpu
FASTSURFER_THREADS=4
```

> **Nota**: Ajusta `FASTSURFER_THREADS` según los cores disponibles en tu sistema. Se recomienda usar el número de cores físicos.

### Iniciar servicios

```bash
docker-compose up -d
```

### Verificar configuración

```bash
curl http://localhost:8000/api/v1/health
```

Respuesta esperada:
```json
{
  "services": {
    "fastsurfer": {
      "gpu_enabled": false
    }
  }
}
```

---

## Modo GPU

El modo GPU acelera significativamente el procesamiento (5-10x más rápido).

### Requisitos previos

1. **Hardware**
   - GPU NVIDIA con 6+ GB VRAM
   - Recomendado: GPUs serie 2000+ (Turing, Ampere, Ada)

2. **Software**
   - Drivers NVIDIA instalados
   - [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

### Instalación de NVIDIA Container Toolkit

**Ubuntu/Debian:**
```bash
# Agregar repositorio
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Instalar
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Reiniciar Docker
sudo systemctl restart docker
```

**Windows (Docker Desktop):**
- Docker Desktop 4.x incluye soporte GPU automáticamente
- Asegúrate de tener WSL2 habilitado
- Instala los drivers NVIDIA para Windows

### Configuración

En el archivo `.env`:

```bash
FASTSURFER_USE_GPU=true
FASTSURFER_DEVICE=cuda
FASTSURFER_THREADS=4
```

### Habilitar GPU en docker-compose.yml

Descomentar la sección `deploy` en el servicio relevante:

```yaml
services:
  app:
    # ... otras configuraciones ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Iniciar servicios

```bash
FASTSURFER_USE_GPU=true docker-compose up -d
```

### Verificar GPU disponible

```bash
# Verificar que Docker detecta la GPU
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Verificar en la API
curl http://localhost:8000/api/v1/health
```

Respuesta esperada:
```json
{
  "services": {
    "fastsurfer": {
      "gpu_enabled": true,
      "status": "healthy"
    }
  }
}
```

---

## Selección de GPU específica

Si tienes múltiples GPUs, puedes especificar cuál usar.

### Por índice de dispositivo

```bash
# Primera GPU
FASTSURFER_DEVICE=cuda:0

# Segunda GPU
FASTSURFER_DEVICE=cuda:1
```

### Por UUID de GPU

Primero, obtén el UUID:
```bash
nvidia-smi -L
# GPU 0: NVIDIA GeForce RTX 3080 (UUID: GPU-12345678-1234-1234-1234-123456789abc)
```

En `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: ['GPU-12345678-1234-1234-1234-123456789abc']
          capabilities: [gpu]
```

### Múltiples GPUs

Para usar todas las GPUs disponibles:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## Troubleshooting

### Error: "Could not select device driver"

**Causa**: NVIDIA Container Toolkit no está instalado correctamente.

**Solución**:
```bash
# Verificar instalación
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Si falla, reinstalar toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Error: "CUDA out of memory"

**Causa**: VRAM insuficiente.

**Soluciones**:
1. Usar modo CPU para procesamiento de alta resolución
2. Reducir resolución de entrada
3. Usar una GPU con más VRAM

```bash
# Fallback a CPU
FASTSURFER_USE_GPU=false
FASTSURFER_DEVICE=cpu
```

### Error: "nvidia-smi not found" en contenedor

**Causa**: Docker no tiene acceso a la GPU.

**Solución Windows (Docker Desktop)**:
1. Abrir Docker Desktop Settings
2. Resources → WSL Integration
3. Habilitar para tu distribución WSL2
4. Reiniciar Docker Desktop

### GPU no detectada en health check

**Verificar**:
```bash
# 1. Drivers funcionando
nvidia-smi

# 2. Docker puede acceder
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# 3. Variables de entorno correctas
cat .env | grep FASTSURFER

# 4. docker-compose.yml tiene sección deploy
grep -A 10 "deploy:" docker-compose.yml
```

---

## Tiempos de procesamiento

### Comparativa CPU vs GPU

| Tipo de Procesamiento | CPU (8 cores) | GPU (RTX 3080) | Speedup |
|-----------------------|---------------|----------------|---------|
| `seg_only`            | 30-60 min     | ~5 min         | 6-12x   |
| `surf_only`           | 90-120 min    | 60-90 min      | 1.3-1.5x |
| `full`                | 2-3 horas     | 60-90 min      | 2-3x    |

### Por resolución de imagen

| Resolución | GPU VRAM mínimo | Tiempo seg_only |
|------------|-----------------|-----------------|
| 1mm        | 6 GB            | ~5 min          |
| 0.8mm      | 8 GB            | ~7 min          |
| 0.7mm      | 10 GB           | ~10 min         |

### Recomendaciones

- **Análisis volumétrico rápido**: `seg_only` con GPU
- **Análisis completo**: `full` con GPU
- **Procesamiento batch**: GPU para paralelizar
- **Recursos limitados**: `seg_only` con CPU es viable (~30-60 min)

---

## Configuración de producción

### Variables de entorno recomendadas

```bash
# Producción con GPU
FASTSURFER_USE_GPU=true
FASTSURFER_DEVICE=cuda
FASTSURFER_THREADS=4
MAX_CONCURRENT_JOBS=2
JOB_TIMEOUT=7200
LOG_LEVEL=WARNING
```

### Monitoreo de GPU

```bash
# Monitoreo en tiempo real
watch -n 1 nvidia-smi

# Logs del contenedor
docker-compose logs -f worker
```

### Múltiples workers con diferentes GPUs

Si tienes múltiples GPUs, puedes crear workers dedicados:

```yaml
# docker-compose.override.yml
services:
  worker-gpu0:
    extends: worker
    environment:
      - FASTSURFER_DEVICE=cuda:0

  worker-gpu1:
    extends: worker
    environment:
      - FASTSURFER_DEVICE=cuda:1
```
