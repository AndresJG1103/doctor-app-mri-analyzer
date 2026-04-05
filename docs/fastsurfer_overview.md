# FastSurfer Overview

## Introducción

FastSurfer es un pipeline de neuroimagen basado en deep learning desarrollado por el laboratorio Deep-MI del Centro Alemán de Enfermedades Neurodegenerativas (DZNE). Proporciona una alternativa rápida y precisa a FreeSurfer para análisis volumétrico y análisis de grosor cortical.

## Características Principales

### Velocidad
- **Segmentación**: ~5 minutos en GPU (vs ~1 hora en FreeSurfer)
- **Reconstrucción de superficie**: ~60-90 minutos (vs ~6-8 horas en FreeSurfer)
- **Pipeline completo**: ~65-95 minutos total

### Precisión
- Resultados comparables a FreeSurfer
- Validado en múltiples datasets
- Publicaciones peer-reviewed

### Compatibilidad
- Compatible con FreeSurfer
- Misma estructura de salida
- Soporta módulos downstream de FreeSurfer

## Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastSurfer Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              SEGMENTATION PIPELINE (~5 min)                  │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │ │
│  │  │  asegdkt  │  │    cc     │  │   cereb   │  │  hypothal │ │ │
│  │  │ FastSurfer│  │  Corpus   │  │ CerebNet  │  │  HypVINN  │ │ │
│  │  │   VINN    │  │ Callosum  │  │           │  │           │ │ │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           SURFACE RECONSTRUCTION (~60-90 min)                │ │
│  │  • Cortical surface extraction                               │ │
│  │  • Thickness analysis                                        │ │
│  │  • Parcellation mapping                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Módulos de Segmentación

### 1. asegdkt (FastSurferVINN)
**Módulo principal de segmentación cerebral**

- Segmentación de 95 clases anatómicas
- Parcelación cortical (atlas DKT)
- Corrección de campo de sesgo
- Estadísticas volumétricas

**Salidas:**
- `aparc.DKTatlas+aseg.deep.mgz`
- `aseg.auto_noCCseg.mgz`
- Estadísticas de volumen

### 2. cc (CorpusCallosum)
**Segmentación del cuerpo calloso**

- Segmentación detallada del CC
- Análisis de grosor
- Métricas de forma
- Estandarización de orientación

**Salidas:**
- Segmentación del CC
- Métricas de forma
- `orient_volume.lta`

### 3. cereb (CerebNet)
**Sub-segmentación del cerebelo**

- Delineación detallada WM/GM
- Sub-regiones cerebelares
- Estadísticas volumétricas

**Salidas:**
- `cerebellum.CerebNet.nii.gz`
- Estadísticas de volumen

### 4. hypothal (HypVINN)
**Sub-segmentación del hipotálamo**

- Segmentación hipotalámica
- 3er ventrículo
- Cuerpo mamilar
- Fórnix y tractos ópticos
- Soporte para imagen T2w adicional

**Salidas:**
- Segmentación hipotalámica
- Estadísticas de subestructuras

## Reconstrucción de Superficie

El pipeline de superficie requiere una **licencia de FreeSurfer** (gratuita).

**Incluye:**
- Extracción de superficies corticales
- Mapeo de etiquetas
- Análisis de grosor punto a punto
- Análisis de ROI

## Requisitos de Entrada

### Calidad de Imagen
- Imágenes MRI T1-weighted de buena calidad
- Preferiblemente escáner 3T
- Sin artefactos significativos de movimiento

### Resolución
- **Recomendada**: 1mm isótropa
- **Soportada**: 0.7mm - 1mm isótropa
- **Experimental**: < 0.7mm

### Secuencias
- Siemens MPRAGE (recomendada)
- Multi-echo MPRAGE
- GE SPGR

### Formatos
- `.nii` (NIfTI)
- `.nii.gz` (NIfTI comprimido)
- `.mgz` (FreeSurfer)

## Requisitos de Sistema

### Recomendado
| Componente | Especificación |
|------------|----------------|
| CPU | Intel/AMD 6+ cores |
| RAM | 16 GB |
| GPU | NVIDIA 2016+ |
| VRAM | 12 GB |

### Mínimos por Modo

| Resolución | Modo | RAM | VRAM |
|------------|------|-----|------|
| 1mm | GPU completo | 8 GB | 6 GB |
| 1mm | GPU parcial | 8 GB | 2 GB |
| 1mm | Solo CPU | 8 GB | - |
| 0.7mm | GPU completo | 8 GB | 8 GB |
| 0.7mm | GPU parcial | 16 GB | 3 GB |

## Modos de Ejecución

### Solo Segmentación (`--seg_only`)
- Tiempo: ~5 minutos (GPU)
- No requiere licencia FreeSurfer
- Ideal para análisis volumétrico rápido

### Solo Superficie (`--surf_only`)
- Tiempo: ~60-90 minutos
- Requiere licencia FreeSurfer
- Requiere segmentación previa

### Pipeline Completo
- Tiempo: ~65-95 minutos
- Requiere licencia FreeSurfer
- Análisis completo

## Integración con Docker

FastSurfer proporciona imágenes Docker oficiales en DockerHub:

```bash
# Imagen con soporte GPU
docker pull deepmi/fastsurfer:latest

# Imagen solo CPU
docker pull deepmi/fastsurfer:cpu-latest
```

### Ejemplo de Ejecución

```bash
docker run --gpus all \
    -v /datos/mri:/data/input:ro \
    -v /datos/salida:/data/output \
    -v /datos/license.txt:/fs_license/license.txt:ro \
    --rm --user $(id -u):$(id -g) \
    deepmi/fastsurfer:latest \
    --t1 /data/input/imagen.nii.gz \
    --sd /data/output \
    --sid sujeto001 \
    --fs_license /fs_license/license.txt \
    --seg_only
```

## Referencias

1. Henschel L, et al. (2020). FastSurfer - A fast and accurate deep learning based neuroimaging pipeline. NeuroImage 219, 117012.

2. Henschel L, Kuegler D, Reuter M. (2022). FastSurferVINN: Building Resolution-Independence into Deep Learning Segmentation Methods. NeuroImage 251, 118933.

3. Faber J, et al. (2022). CerebNet: A fast and reliable deep-learning pipeline for detailed cerebellum sub-segmentation. NeuroImage 264, 119703.

4. Estrada S, et al. (2023). FastSurfer-HypVINN: Automated sub-segmentation of the hypothalamus. Imaging Neuroscience 1, 1–32.

## Recursos

- **GitHub**: https://github.com/Deep-MI/FastSurfer
- **DockerHub**: https://hub.docker.com/r/deepmi/fastsurfer
- **Documentación**: https://github.com/Deep-MI/FastSurfer/tree/stable/doc
