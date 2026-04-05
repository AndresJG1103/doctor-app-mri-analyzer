# MRI Report API

API FastAPI para procesamiento de imágenes MRI utilizando [FastSurfer](https://github.com/Deep-MI/FastSurfer).

![FastSurfer](https://img.shields.io/badge/FastSurfer-Deep--MI-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

## 📋 Descripción

Este proyecto proporciona una API REST para el procesamiento asíncrono de imágenes de resonancia magnética (MRI) del cerebro utilizando FastSurfer, un pipeline de neuroimagen basado en deep learning.

### Características

- ✅ **API REST con FastAPI** - Framework moderno y de alto rendimiento
- ✅ **Procesamiento Asíncrono** - Jobs encolados con Redis
- ✅ **Integración FastSurfer** - Segmentación y análisis automático
- ✅ **Docker Compose** - Orquestación completa de servicios
- ✅ **Soporte GPU** - Configurable via variables de entorno
- ✅ **Documentación Automática** - Swagger UI y ReDoc

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   FastAPI App   │     Redis       │     FastSurfer Container    │
│   (Port 8000)   │   (Port 6379)   │     (GPU/CPU support)       │
├─────────────────┴─────────────────┴─────────────────────────────┤
│                     Shared Volumes                               │
│   /data/input    /data/output    /data/licenses                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Requisitos

### Software
- Docker 20.10+
- Docker Compose 2.0+
- (Opcional) NVIDIA GPU + NVIDIA Container Toolkit para aceleración GPU

### Sistema (para procesamiento GPU)
- CPU Intel/AMD (6+ cores)
- 16 GB RAM
- GPU NVIDIA (6+ GB VRAM)

### Licencia FreeSurfer
Para usar el pipeline de superficie (`surf_only` o `full`), necesitas una licencia gratuita de FreeSurfer:
1. Regístrate en: https://surfer.nmr.mgh.harvard.edu/registration.html
2. Coloca el archivo `license.txt` en `data/licenses/`

## 🚀 Inicio Rápido

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd mri_report
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env según necesidades
```

### 3. Crear directorios de datos

```bash
mkdir -p data/input data/output data/licenses
# Copiar licencia de FreeSurfer si es necesario
cp /path/to/freesurfer/license.txt data/licenses/
```

### 4. Verificar que todo funciona

```bash
curl http://localhost:8000/api/v1/health
```

### 5. Acceder a la documentación

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

---

## 🐳 Docker: Desarrollo vs Producción

### Desarrollo (con hot-reload)

Para desarrollo local con Docker, usa el modo de desarrollo que monta el código fuente y permite hot-reload:

```bash
# 1. Configurar variables de entorno
cp .env.example .env

# 2. Iniciar servicios en modo desarrollo (CPU)
docker-compose up --build

# Con logs en tiempo real
docker-compose up --build 2>&1 | tee logs/docker.log

# En segundo plano
docker-compose up -d --build

# Ver logs
docker-compose logs -f api
docker-compose logs -f worker
```

**Características del modo desarrollo:**
- ✅ Código fuente montado como volumen (cambios reflejados sin rebuild)
- ✅ Logs detallados visibles
- ✅ Rebuild automático con `--build`

#### Desarrollo sin Docker (recomendado para debugging)

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o en Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -e ".[dev]"

# 3. Iniciar Redis (necesario)
docker run -d -p 6379:6379 --name redis-dev redis:7-alpine

# 4. Ejecutar API con hot-reload
cd src && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. En otra terminal, ejecutar worker
cd src && python -m app.workers.mri_worker
```

---

### Producción

Para despliegue en producción, sigue estos pasos:

#### Producción sin GPU (CPU)

```bash
# 1. Configurar variables de producción
cp .env.example .env
# Editar .env con valores de producción:
#   - FASTSURFER_USE_GPU=false
#   - FASTSURFER_DEVICE=cpu
#   - FASTSURFER_THREADS=4  (ajustar según cores disponibles)

# 2. Establecer HOST_DATA_PATH (IMPORTANTE para Docker-in-Docker)
export HOST_DATA_PATH=$(pwd)/data

# 3. Construir imágenes optimizadas
docker-compose build --no-cache

# 4. Iniciar servicios en producción
docker-compose up -d

# 5. Verificar estado
docker-compose ps
curl http://localhost:8000/api/v1/health
```

#### Producción con GPU (NVIDIA)

**Requisitos previos:**
1. GPU NVIDIA con 6+ GB VRAM
2. Drivers NVIDIA instalados (`nvidia-smi` debe funcionar)
3. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) instalado

```bash
# 1. Verificar que Docker detecta la GPU
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# 2. Configurar variables para GPU
cp .env.example .env
# Editar .env:
#   - FASTSURFER_USE_GPU=true
#   - FASTSURFER_DEVICE=cuda      (o cuda:0, cuda:1 para GPU específica)

# 3. Establecer HOST_DATA_PATH
export HOST_DATA_PATH=$(pwd)/data

# 4. Iniciar servicios con GPU
FASTSURFER_USE_GPU=true docker-compose up -d --build

# 5. Verificar que el worker tiene acceso a GPU
docker-compose logs worker | grep -i gpu
```

**Nota:** El archivo `docker-compose.yml` ya incluye la sección de deploy para GPU. Si no usas GPU, puedes comentar esa sección para evitar errores.

#### Comandos útiles de producción

```bash
# Ver estado de todos los servicios
docker-compose ps

# Ver logs de un servicio específico
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f redis

# Reiniciar un servicio
docker-compose restart api

# Escalar workers (procesar múltiples jobs en paralelo)
docker-compose up -d --scale worker=3

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (¡CUIDADO: elimina datos!)
docker-compose down -v

# Actualizar imágenes y reiniciar
docker-compose pull
docker-compose up -d --build
```

#### Tiempos de procesamiento estimados

| Tipo | CPU (4 cores) | GPU (6GB VRAM) |
|------|---------------|----------------|
| `seg_only` | ~30-60 min | ~5 min |
| `surf_only` | ~90-120 min | ~60-90 min |
| `full` | ~2-3 horas | ~60-90 min |

---

### Variables de entorno importantes

| Variable | Desarrollo | Producción | Descripción |
|----------|------------|------------|-------------|
| `FASTSURFER_USE_GPU` | `false` | `true/false` | Habilitar GPU |
| `FASTSURFER_DEVICE` | `cpu` | `cuda` | Dispositivo de procesamiento |
| `FASTSURFER_THREADS` | `2` | `4-8` | Threads CPU |
| `HOST_DATA_PATH` | No requerido | **Requerido** | Path absoluto a `./data` en el host |
| `MAX_UPLOAD_SIZE` | `524288000` | `524288000` | Máximo 500MB |

> ⚠️ **Importante:** `HOST_DATA_PATH` es necesario en producción porque el worker usa Docker-in-Docker y necesita montar volúmenes con paths del host.

## 📖 Uso de la API

### Procesar un archivo MRI

```bash
curl -X POST "http://localhost:8000/api/v1/mri/process" \
  -F "file=@/path/to/brain.nii.gz" \
  -F "processing_type=seg_only" \
  -F "subject_id=patient001"
```

**Tipos de procesamiento:**
- `seg_only`: Solo segmentación (~5 min GPU)
- `surf_only`: Solo superficie (~60-90 min, requiere licencia FreeSurfer)
- `full`: Pipeline completo

### Consultar estado del job

```bash
curl "http://localhost:8000/api/v1/mri/jobs/{job_id}"
```

### Obtener resultados

```bash
curl "http://localhost:8000/api/v1/mri/jobs/{job_id}/results"
```

### Ejemplo completo con Python

```python
import requests
import time

# Subir archivo
with open("brain.nii.gz", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/mri/process",
        files={"file": f},
        data={"processing_type": "seg_only", "subject_id": "patient001"},
    )

job_id = response.json()["job_id"]

# Esperar procesamiento
while True:
    status = requests.get(f"http://localhost:8000/api/v1/mri/jobs/{job_id}").json()
    print(f"Status: {status['status']}, Progress: {status['progress']}%")
    
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(10)

# Obtener resultados
if status["status"] == "completed":
    results = requests.get(f"http://localhost:8000/api/v1/mri/jobs/{job_id}/results")
    print(results.json())
```

## ⚙️ Configuración

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `FASTSURFER_USE_GPU` | `false` | Habilitar procesamiento GPU |
| `FASTSURFER_DEVICE` | `cpu` | Dispositivo: cpu, cuda, cuda:0 |
| `FASTSURFER_THREADS` | `4` | Threads de procesamiento |
| `FASTSURFER_IMAGE` | `deepmi/fastsurfer:latest` | Imagen Docker de FastSurfer |
| `MAX_UPLOAD_SIZE` | `524288000` | Tamaño máximo de archivo (500MB) |
| `REDIS_HOST` | `redis` | Host de Redis |

Ver `.env.example` para lista completa.

## 📁 Estructura del Proyecto

```
mri_report/
├── docker-compose.yml          # Orquestación de servicios
├── Dockerfile                  # Imagen de la API
├── requirements.txt            # Dependencias Python
├── .env.example               # Variables de entorno de ejemplo
│
├── src/app/                   # Código de la aplicación
│   ├── api/v1/endpoints/      # Endpoints de la API
│   ├── core/                  # Configuración y utilidades
│   ├── models/                # Schemas Pydantic
│   ├── services/              # Lógica de negocio
│   └── workers/               # Workers de procesamiento
│
├── tests/                     # Tests
├── docs/                      # Documentación
├── scripts/                   # Scripts de utilidad
└── data/                      # Datos (gitignored)
    ├── input/                 # Archivos MRI de entrada
    ├── output/                # Resultados de FastSurfer
    └── licenses/              # Licencias
```

## 🧪 Testing

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Ejecutar tests
pytest

# Con cobertura
pytest --cov=app tests/

# Solo tests de API
pytest tests/api/
```

## 📊 Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/health` | Estado de salud |
| GET | `/api/v1/health/live` | Liveness probe |
| GET | `/api/v1/health/ready` | Readiness probe |
| POST | `/api/v1/mri/process` | Procesar archivo MRI |
| GET | `/api/v1/mri/jobs` | Listar jobs |
| GET | `/api/v1/mri/jobs/{id}` | Estado de un job |
| GET | `/api/v1/mri/jobs/{id}/results` | Resultados de un job |
| DELETE | `/api/v1/mri/jobs/{id}` | Cancelar job |

## 📚 Documentación Adicional

- [FastSurfer Overview](docs/fastsurfer_overview.md)
- [FastSurfer Modules](docs/fastsurfer_modules.md)
- [API Guide](docs/api_guide.md)

## 🔗 Referencias

- [FastSurfer Repository](https://github.com/Deep-MI/FastSurfer)
- [FastSurfer Paper](https://doi.org/10.1016/j.neuroimage.2020.117012)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FreeSurfer](https://freesurfer.net/)

## ⚠️ Aviso Importante

Este software es para **propósitos de investigación únicamente**. No debe usarse para diagnóstico clínico o decisiones de tratamiento en pacientes individuales.

## 📄 Licencia

MIT License

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request
