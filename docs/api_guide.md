# MRI Report API - Guía de Uso

## Descripción General

La MRI Report API permite procesar imágenes de resonancia magnética (MRI) utilizando FastSurfer de manera asíncrona a través de una API REST.

## URL Base

```
http://localhost:8000/api/v1
```

## Autenticación

Actualmente la API no requiere autenticación. En producción, se recomienda implementar autenticación apropiada.

---

## Endpoints

### Health Check

#### GET /health
Verifica el estado de la API y sus dependencias.

**Respuesta:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-02-27T03:45:00Z",
  "services": {
    "redis": {
      "status": "healthy",
      "latency_ms": 1.23,
      "version": "7.0.0"
    },
    "fastsurfer": {
      "status": "healthy",
      "docker": "connected",
      "image_available": true,
      "gpu_enabled": false
    }
  }
}
```

#### GET /health/live
Verificación simple de disponibilidad (liveness probe).

#### GET /health/ready
Verificación de preparación para recibir requests (readiness probe).

---

### Procesamiento MRI

#### POST /mri/process
Sube un archivo MRI y lo encola para procesamiento.

**Request:**
- Content-Type: `multipart/form-data`

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| file | File | Sí | Archivo MRI (.nii, .nii.gz, .mgz) |
| processing_type | string | Sí | Tipo de procesamiento |
| subject_id | string | No | ID del sujeto (auto-generado si no se proporciona) |
| threads | integer | No | Número de threads (default: 4) |
| use_3T_atlas | boolean | No | Usar atlas 3T (default: true) |
| no_biasfield | boolean | No | Omitir corrección de campo de sesgo |
| no_cereb | boolean | No | Omitir segmentación de cerebelo |
| no_hypothal | boolean | No | Omitir segmentación de hipotálamo |

**Valores de processing_type:**
- `seg_only`: Solo segmentación (~5 min)
- `surf_only`: Solo reconstrucción de superficie (~60-90 min)
- `full`: Pipeline completo

**Ejemplo con cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/mri/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/brain.nii.gz" \
  -F "processing_type=seg_only" \
  -F "subject_id=patient001" \
  -F "threads=4" \
  -F "use_3T_atlas=true"
```

**Respuesta (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "subject_id": "patient001",
  "processing_type": "seg_only",
  "created_at": "2026-02-27T03:45:00Z",
  "message": "Job enqueued successfully"
}
```

**Errores:**
- `400`: Archivo inválido o extensión no permitida
- `413`: Archivo demasiado grande (max 500MB)
- `422`: Error de validación

---

#### GET /mri/jobs
Lista todos los jobs con paginación.

**Parámetros de Query:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| page | integer | 1 | Número de página |
| page_size | integer | 10 | Elementos por página (max 100) |
| status_filter | string | null | Filtrar por estado |

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/mri/jobs?page=1&page_size=10&status_filter=completed"
```

**Respuesta:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "subject_id": "patient001",
      "processing_type": "seg_only",
      "created_at": "2026-02-27T03:45:00Z",
      "started_at": "2026-02-27T03:45:05Z",
      "completed_at": "2026-02-27T03:50:00Z",
      "progress": 100,
      "error_message": null,
      "output_path": "/data/output/patient001",
      "input_file": "brain.nii.gz"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

---

#### GET /mri/jobs/{job_id}
Obtiene el estado de un job específico.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/mri/jobs/550e8400-e29b-41d4-a716-446655440000"
```

**Respuesta:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "subject_id": "patient001",
  "processing_type": "seg_only",
  "created_at": "2026-02-27T03:45:00Z",
  "started_at": "2026-02-27T03:45:05Z",
  "completed_at": null,
  "progress": 65,
  "error_message": null,
  "output_path": null,
  "input_file": "brain.nii.gz"
}
```

**Estados posibles:**
- `queued`: En cola, esperando procesamiento
- `processing`: Procesándose actualmente
- `completed`: Completado exitosamente
- `failed`: Falló (ver error_message)
- `cancelled`: Cancelado por el usuario

---

#### GET /mri/jobs/{job_id}/results
Obtiene los resultados de un job completado.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/mri/jobs/550e8400-e29b-41d4-a716-446655440000/results"
```

**Respuesta:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "subject_id": "patient001",
  "output_path": "/data/output/patient001",
  "files": [
    "mri/aparc.DKTatlas+aseg.deep.mgz",
    "mri/brainmask.mgz",
    "mri/orig.mgz",
    "stats/aseg.stats"
  ],
  "statistics": {
    "stats_file": "/data/output/patient001/stats/aseg.stats"
  }
}
```

**Errores:**
- `400`: Job no está completado
- `404`: Job no encontrado o resultados no disponibles

---

#### DELETE /mri/jobs/{job_id}
Cancela un job en cola.

**Ejemplo:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/mri/jobs/550e8400-e29b-41d4-a716-446655440000"
```

**Respuesta:** `204 No Content`

**Errores:**
- `400`: Job no se puede cancelar (no está en estado queued)
- `404`: Job no encontrado

---

## Flujo de Trabajo Típico

```
1. Subir archivo MRI
   POST /mri/process
   → Obtener job_id

2. Consultar estado periódicamente
   GET /mri/jobs/{job_id}
   → Verificar status y progress

3. Cuando status == "completed"
   GET /mri/jobs/{job_id}/results
   → Obtener lista de archivos de salida

4. Acceder a archivos
   Los archivos están en: /data/output/{subject_id}/
```

---

## Ejemplos con Python

### Usando requests

```python
import requests
import time

# 1. Subir archivo
with open("brain.nii.gz", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/mri/process",
        files={"file": ("brain.nii.gz", f)},
        data={
            "processing_type": "seg_only",
            "subject_id": "patient001",
        },
    )

job = response.json()
job_id = job["job_id"]
print(f"Job created: {job_id}")

# 2. Esperar procesamiento
while True:
    response = requests.get(f"http://localhost:8000/api/v1/mri/jobs/{job_id}")
    status = response.json()
    
    print(f"Status: {status['status']}, Progress: {status['progress']}%")
    
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    
    time.sleep(10)

# 3. Obtener resultados
if status["status"] == "completed":
    response = requests.get(f"http://localhost:8000/api/v1/mri/jobs/{job_id}/results")
    results = response.json()
    print(f"Output files: {results['files']}")
```

### Usando httpx (async)

```python
import httpx
import asyncio

async def process_mri(filepath: str, subject_id: str):
    async with httpx.AsyncClient() as client:
        # Subir archivo
        with open(filepath, "rb") as f:
            response = await client.post(
                "http://localhost:8000/api/v1/mri/process",
                files={"file": (filepath, f)},
                data={
                    "processing_type": "seg_only",
                    "subject_id": subject_id,
                },
            )
        
        job = response.json()
        job_id = job["job_id"]
        
        # Esperar completado
        while True:
            response = await client.get(
                f"http://localhost:8000/api/v1/mri/jobs/{job_id}"
            )
            status = response.json()
            
            if status["status"] == "completed":
                return await client.get(
                    f"http://localhost:8000/api/v1/mri/jobs/{job_id}/results"
                )
            elif status["status"] in ["failed", "cancelled"]:
                raise Exception(f"Job failed: {status.get('error_message')}")
            
            await asyncio.sleep(10)

# Ejecutar
results = asyncio.run(process_mri("brain.nii.gz", "patient001"))
print(results.json())
```

---

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 200 | Éxito |
| 202 | Aceptado (job creado) |
| 204 | Sin contenido (operación exitosa) |
| 400 | Solicitud inválida |
| 404 | Recurso no encontrado |
| 413 | Archivo demasiado grande |
| 422 | Error de validación |
| 500 | Error interno del servidor |
| 503 | Servicio no disponible |

---

## Límites

| Límite | Valor |
|--------|-------|
| Tamaño máximo de archivo | 500 MB |
| Extensiones permitidas | .nii, .nii.gz, .mgz |
| Longitud máxima de subject_id | 64 caracteres |
| Caracteres permitidos en subject_id | a-z, A-Z, 0-9, -, _ |
| Jobs por página (máximo) | 100 |

---

## Documentación Interactiva

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json
