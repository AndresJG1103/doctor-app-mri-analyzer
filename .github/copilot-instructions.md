# Copilot Instructions for MRI Report API

FastAPI service for MRI brain image processing using FastSurfer. Processes neuroimaging files (.nii, .nii.gz, .mgz) through async job queues with Redis backend.

## Build, Test, and Lint

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/api/test_health.py

# Run a single test by name
pytest -k "test_health_check_returns_200"

# Run with coverage
pytest --cov=app tests/

# Linting
ruff check src/
black --check src/

# Type checking
mypy src/
```

### Running Locally (without Docker)

```bash
# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Run API (from project root)
cd src && python -m uvicorn app.main:app --reload

# Run worker in separate terminal
cd src && python -m app.workers.mri_worker
```

### Running with Docker

```bash
docker-compose up -d

# With GPU support
FASTSURFER_USE_GPU=true docker-compose up -d
```

## Architecture

### Service Components

```
┌────────────────┐     ┌─────────┐     ┌───────────────────┐
│  FastAPI App   │────▶│  Redis  │◀────│   MRI Worker      │
│  (API Layer)   │     │ (Queue) │     │ (Job Processor)   │
└────────────────┘     └─────────┘     └─────────┬─────────┘
                                                 │
                                       ┌─────────▼─────────┐
                                       │ FastSurfer Docker │
                                       │   (Processing)    │
                                       └───────────────────┘
```

- **API Layer** (`src/app/api/`): Handles HTTP requests, file uploads, job creation
- **Job Manager** (`src/app/services/job_manager.py`): Redis-backed job state machine (queued → processing → completed/failed)
- **MRI Worker** (`src/app/workers/mri_worker.py`): Polls queue, orchestrates FastSurfer container execution
- **FastSurfer Service** (`src/app/services/fastsurfer.py`): Docker SDK integration for running FastSurfer containers

### Request Flow

1. Client uploads MRI file to `/api/v1/mri/process`
2. File saved to `DATA_INPUT_DIR`, job created in Redis with status `queued`
3. Worker picks up job, launches FastSurfer Docker container with mounted volumes
4. Worker updates job progress/status in Redis
5. Client polls `/api/v1/mri/jobs/{id}` for status, retrieves results when complete

### Key Data Models

- `ProcessingType`: `seg_only` (fast), `surf_only` (requires FreeSurfer license), `full`
- `JobStatus`: `queued` → `processing` → `completed`/`failed`/`cancelled`

## Code Conventions

### Project Structure

```
src/app/
├── api/v1/endpoints/   # Route handlers (thin layer, delegate to services)
├── core/               # Config (pydantic-settings), Redis client singleton
├── models/schemas.py   # All Pydantic models (request/response schemas)
├── services/           # Business logic (job_manager, fastsurfer)
└── workers/            # Background job processors
```

### Patterns

- **Configuration**: All settings via `pydantic-settings` in `core/config.py`, loaded from environment/`.env`
- **Global Singletons**: Services instantiated at module level (`fastsurfer_service`, `job_manager`, `redis_client`)
- **Schemas**: All Pydantic models in `models/schemas.py`, using `ConfigDict(extra="forbid")` for strict validation
- **API Versioning**: Routes prefixed with `/api/v1`, configured in `core/config.py`
- **Testing**: Fixtures in `tests/conftest.py` mock Redis and services; use `TestClient` from FastAPI

### Type Hints

Project uses strict mypy (`strict = true`). All functions require type annotations except `self`/`cls`.

### Docker-in-Docker

When running inside Docker, the FastSurfer service needs host paths for volume mounts. Set `HOST_DATA_PATH` environment variable to the absolute host path of the `data/` directory.

## Configuración CPU/GPU

### Modo CPU (por defecto)

En `.env`:
```bash
FASTSURFER_USE_GPU=false
FASTSURFER_DEVICE=cpu
FASTSURFER_THREADS=4  # Ajustar según cores disponibles
```

Iniciar servicios:
```bash
docker-compose up -d
```

### Modo GPU (NVIDIA)

**Requisitos previos:**
1. GPU NVIDIA con 6+ GB VRAM
2. Drivers NVIDIA instalados
3. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

**Configuración en `.env`:**
```bash
FASTSURFER_USE_GPU=true
FASTSURFER_DEVICE=cuda      # GPU por defecto
# FASTSURFER_DEVICE=cuda:0  # GPU específica
# FASTSURFER_DEVICE=cuda:1  # Segunda GPU
```

**Habilitar GPU en `docker-compose.yml`:**

Descomentar la sección `deploy` en el servicio `fastsurfer`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

**Iniciar servicios:**
```bash
FASTSURFER_USE_GPU=true docker-compose up -d
```

**Verificar GPU:**
```bash
# Verificar que Docker detecta la GPU
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Tiempos de Procesamiento Estimados

| Tipo | CPU | GPU |
|------|-----|-----|
| `seg_only` | ~30-60 min | ~5 min |
| `surf_only` | ~90-120 min | ~60-90 min |
| `full` | ~2-3 horas | ~60-90 min |
