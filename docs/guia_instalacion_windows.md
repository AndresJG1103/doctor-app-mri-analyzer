# Guía de Instalación en Windows (desde cero)

Esta guía te lleva paso a paso desde un Windows limpio hasta tener el sistema funcionando con CPU o GPU.

## Índice

1. [Requisitos del sistema](#requisitos-del-sistema)
2. [Instalación de prerrequisitos](#instalación-de-prerrequisitos)
3. [Configuración del proyecto](#configuración-del-proyecto)
4. [Modo CPU](#modo-cpu)
5. [Modo GPU](#modo-gpu)
6. [Verificación](#verificación)
7. [Solución de problemas](#solución-de-problemas)

---

## Requisitos del sistema

### Mínimos (CPU)
- Windows 10 versión 2004+ o Windows 11
- 16 GB RAM
- 50 GB espacio en disco
- Procesador con virtualización habilitada (VT-x/AMD-V)

### Recomendados (GPU)
- Todo lo anterior, más:
- GPU NVIDIA con 6+ GB VRAM (serie GTX 1060 o superior)
- Drivers NVIDIA actualizados

---

## Instalación de prerrequisitos

### Paso 1: Habilitar virtualización en BIOS

1. Reiniciar el PC y entrar al BIOS (generalmente F2, F10, DEL, o ESC durante el arranque)
2. Buscar opciones como:
   - Intel: "Intel Virtualization Technology" o "VT-x"
   - AMD: "SVM Mode" o "AMD-V"
3. Habilitar la opción
4. Guardar y reiniciar

### Paso 2: Habilitar WSL2

Abrir **PowerShell como Administrador** y ejecutar:

```powershell
# Habilitar WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Habilitar Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

**Reiniciar Windows**

Después del reinicio, en PowerShell como Administrador:

```powershell
# Establecer WSL2 como versión por defecto
wsl --set-default-version 2

# Actualizar WSL
wsl --update
```

### Paso 3: Instalar distribución Linux para WSL2

```powershell
# Instalar Ubuntu (recomendado)
wsl --install -d Ubuntu

# O listar distribuciones disponibles
wsl --list --online
```

Después de instalar, se abrirá Ubuntu y pedirá crear usuario y contraseña.

### Paso 4: Instalar Docker Desktop

1. Descargar Docker Desktop desde: https://www.docker.com/products/docker-desktop/

2. Ejecutar el instalador con las opciones:
   - ✅ Use WSL 2 instead of Hyper-V
   - ✅ Add shortcut to desktop

3. **Reiniciar Windows** después de la instalación

4. Abrir Docker Desktop y completar la configuración inicial

5. Verificar instalación en PowerShell:
```powershell
docker --version
docker run hello-world
```

### Paso 5: Instalar Git

1. Descargar desde: https://git-scm.com/download/win

2. Instalar con opciones por defecto

3. Verificar:
```powershell
git --version
```

### Paso 6: Instalar Python (opcional, para desarrollo)

1. Descargar Python 3.10+ desde: https://www.python.org/downloads/

2. **IMPORTANTE**: Marcar ✅ "Add Python to PATH" durante instalación

3. Verificar:
```powershell
python --version
pip --version
```

---

## Configuración del proyecto

### Paso 1: Clonar el repositorio

```powershell
cd C:\Users\TuUsuario\Projects
git clone <url-del-repositorio> mri_report
cd mri_report
```

### Paso 2: Crear estructura de datos

```powershell
# Crear directorios necesarios
mkdir data\input
mkdir data\output
mkdir data\licenses
```

### Paso 3: Configurar variables de entorno

```powershell
# Copiar archivo de ejemplo
copy .env.example .env

# Abrir para editar
notepad .env
```

### Paso 4: Configurar HOST_DATA_PATH

En el archivo `.env`, configurar la ruta absoluta a la carpeta `data`:

```bash
# IMPORTANTE: Usar barras normales (/), no backslashes (\)
HOST_DATA_PATH=C:/Users/TuUsuario/Projects/mri_report/data
```

> **Nota**: Docker en Windows requiere rutas con `/` no `\`

---

## Modo CPU

### Configuración

Editar `.env`:

```bash
# Configuración CPU
FASTSURFER_USE_GPU=false
FASTSURFER_DEVICE=cpu
FASTSURFER_THREADS=4

# Ruta de datos (ajustar a tu ruta)
HOST_DATA_PATH=C:/Users/TuUsuario/Projects/mri_report/data
```

### Ajustar threads según tu CPU

| Cores CPU | FASTSURFER_THREADS recomendado |
|-----------|--------------------------------|
| 4 cores   | 4                              |
| 6 cores   | 4-6                            |
| 8+ cores  | 6-8                            |

### Iniciar servicios

```powershell
# Iniciar en modo detached
docker-compose up -d

# Ver logs
docker-compose logs -f

# Verificar estado
docker-compose ps
```

### Detener servicios

```powershell
docker-compose down
```

---

## Modo GPU

### Paso 1: Verificar GPU compatible

```powershell
# Ver información de GPU
nvidia-smi
```

Deberías ver algo como:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx.xx    Driver Version: 535.xx.xx    CUDA Version: 12.x    |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0  On |                  N/A |
|  0%   45C    P8    15W / 250W |    500MiB / 12288MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

Si no funciona, instalar/actualizar drivers NVIDIA:
- https://www.nvidia.com/Download/index.aspx

### Paso 2: Configurar Docker Desktop para GPU

1. Abrir **Docker Desktop**

2. Ir a ⚙️ **Settings** → **Resources** → **WSL Integration**

3. Habilitar integración con tu distribución Ubuntu:
   - ✅ Enable integration with my default WSL distro
   - ✅ Ubuntu (o la distro que instalaste)

4. Click **Apply & Restart**

### Paso 3: Verificar GPU en Docker

```powershell
# Probar acceso a GPU desde Docker
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

Deberías ver la misma salida de `nvidia-smi` que antes.

**Si falla**, ver [Solución de problemas](#gpu-no-detectada-en-docker).

### Paso 4: Configurar .env para GPU

```bash
# Configuración GPU
FASTSURFER_USE_GPU=true
FASTSURFER_DEVICE=cuda
FASTSURFER_THREADS=4

# Ruta de datos
HOST_DATA_PATH=C:/Users/TuUsuario/Projects/mri_report/data
```

### Paso 5: Habilitar GPU en docker-compose.yml

Abrir `docker-compose.yml` y descomentar la sección `deploy`:

```yaml
services:
  app:
    # ... otras configuraciones ...
    
    # Descomentar estas líneas para GPU:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Paso 6: Iniciar servicios con GPU

```powershell
# Iniciar
docker-compose up -d

# Verificar GPU habilitada
curl http://localhost:8000/api/v1/health
```

---

## Verificación

### Verificar servicios corriendo

```powershell
# Estado de contenedores
docker-compose ps

# Debería mostrar algo como:
# NAME                STATUS
# mri_report-app-1    Up
# mri_report-redis-1  Up
```

### Verificar API funcionando

```powershell
# Health check
curl http://localhost:8000/api/v1/health

# O en navegador:
# http://localhost:8000/api/v1/docs
```

### Verificar configuración GPU/CPU

```powershell
curl http://localhost:8000/api/v1/health
```

Buscar en la respuesta:
```json
{
  "services": {
    "fastsurfer": {
      "gpu_enabled": true,  // o false para CPU
      "status": "healthy"
    }
  }
}
```

### Prueba de procesamiento

```powershell
# Colocar archivo MRI de prueba en data/input/
copy tu_archivo.nii.gz data\input\

# Enviar a procesar
curl -X POST "http://localhost:8000/api/v1/mri/process" ^
  -F "file=@data\input\tu_archivo.nii.gz" ^
  -F "processing_type=seg_only" ^
  -F "subject_id=test001"
```

---

## Solución de problemas

### WSL2 no se instala

**Error**: "WslRegisterDistribution failed with error: 0x80370102"

**Solución**:
1. Verificar virtualización habilitada en BIOS
2. En PowerShell como Admin:
```powershell
bcdedit /set hypervisorlaunchtype auto
```
3. Reiniciar Windows

### Docker Desktop no inicia

**Error**: "Docker Desktop requires Windows 10 Pro/Enterprise"

**Solución**: Docker Desktop funciona con Windows 10 Home con WSL2. Asegurarse de:
1. Windows actualizado (versión 2004+)
2. WSL2 instalado correctamente

**Verificar versión de Windows**:
```powershell
winver
```

### GPU no detectada en Docker

**Error**: "docker: Error response from daemon: could not select device driver"

**Soluciones**:

1. **Actualizar drivers NVIDIA** a la última versión:
   - https://www.nvidia.com/Download/index.aspx

2. **Actualizar WSL**:
```powershell
wsl --update
wsl --shutdown
```

3. **Reiniciar Docker Desktop**

4. **Verificar CUDA en WSL**:
```powershell
wsl
nvidia-smi
```

5. **Si nada funciona**, reinstalar drivers NVIDIA con "Clean Install"

### Error "CUDA out of memory"

**Causa**: GPU no tiene suficiente VRAM.

**Soluciones**:
1. Cerrar otras aplicaciones que usen GPU
2. Usar modo CPU:
```bash
FASTSURFER_USE_GPU=false
FASTSURFER_DEVICE=cpu
```

### Error de conexión a Redis

**Error**: "Cannot connect to Redis"

**Solución**:
```powershell
# Verificar que Redis está corriendo
docker-compose ps

# Reiniciar servicios
docker-compose down
docker-compose up -d
```

### Archivos de salida sin permisos

**Error**: No se pueden leer archivos en `data/output/`

**Solución**: Agregar permisos en WSL:
```bash
wsl
sudo chmod -R 777 /mnt/c/Users/TuUsuario/Projects/mri_report/data/output
```

### Puerto 8000 en uso

**Error**: "Bind for 0.0.0.0:8000 failed: port is already allocated"

**Solución**:
```powershell
# Encontrar proceso usando el puerto
netstat -ano | findstr :8000

# Matar proceso (reemplazar PID)
taskkill /PID <PID> /F

# O cambiar puerto en .env
PORT=8001
```

---

## Comandos útiles

### Docker

```powershell
# Ver logs en tiempo real
docker-compose logs -f

# Logs de un servicio específico
docker-compose logs -f app

# Reiniciar un servicio
docker-compose restart app

# Reconstruir imágenes
docker-compose build --no-cache

# Limpiar todo y empezar de nuevo
docker-compose down -v
docker system prune -a
```

### GPU

```powershell
# Monitoreo de GPU en tiempo real
nvidia-smi -l 1

# Ver procesos usando GPU
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv

# Información detallada
nvidia-smi -q
```

### WSL

```powershell
# Reiniciar WSL
wsl --shutdown

# Ver distribuciones instaladas
wsl --list --verbose

# Entrar a Ubuntu
wsl

# Ejecutar comando en WSL
wsl ls -la /mnt/c/Users
```

---

## Resumen de configuración

### CPU (configuración mínima)

`.env`:
```bash
FASTSURFER_USE_GPU=false
FASTSURFER_DEVICE=cpu
FASTSURFER_THREADS=4
HOST_DATA_PATH=C:/Users/TuUsuario/Projects/mri_report/data
```

### GPU (configuración recomendada)

`.env`:
```bash
FASTSURFER_USE_GPU=true
FASTSURFER_DEVICE=cuda
FASTSURFER_THREADS=4
HOST_DATA_PATH=C:/Users/TuUsuario/Projects/mri_report/data
```

`docker-compose.yml` - descomentar sección `deploy` con GPU.
