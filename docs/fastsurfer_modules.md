# FastSurfer Modules

Este documento describe en detalle cada módulo de FastSurfer y sus opciones de configuración.

## Índice

1. [FastSurferVINN (asegdkt)](#fastsurfervinn-asegdkt)
2. [CorpusCallosum (cc)](#corpuscallosum-cc)
3. [CerebNet (cereb)](#cerebnet-cereb)
4. [HypVINN (hypothal)](#hypvinn-hypothal)
5. [Recon-Surf (superficie)](#recon-surf-superficie)

---

## FastSurferVINN (asegdkt)

### Descripción
FastSurferVINN es el módulo central de segmentación que utiliza una red neuronal convolucional (CNN) para segmentar el cerebro completo en 95 clases anatómicas.

### Arquitectura
- Red 2.5D con agregación de vistas (sagital, coronal, axial)
- Resolución independiente (VINN - View-aggregation Independence Neural Network)
- Entrenada en datos de FreeSurfer

### Salidas

| Archivo | Descripción |
|---------|-------------|
| `aparc.DKTatlas+aseg.deep.mgz` | Segmentación principal con parcelación cortical |
| `aseg.auto_noCCseg.mgz` | Segmentación sin cuerpo calloso |
| `brainmask.mgz` | Máscara del cerebro |
| `orig.mgz` | Imagen conformada |
| `stats/aseg.stats` | Estadísticas volumétricas |

### Opciones

```bash
--no_asegdkt          # Desactivar este módulo
--no_biasfield        # Omitir corrección de campo de sesgo
--asegdkt_segfile     # Ruta personalizada para salida
```

### Clases Segmentadas
- Ventrículos (lateral, 3rd, 4th)
- Sustancia blanca
- Corteza cerebral
- Estructuras subcorticales (tálamo, putamen, caudado, etc.)
- Cerebelo
- Tronco encefálico
- 34 regiones corticales por hemisferio (atlas DKT)

---

## CorpusCallosum (cc)

### Descripción
Módulo especializado para la segmentación y análisis morfométrico del cuerpo calloso.

### Funcionalidades
- Segmentación detallada del cuerpo calloso
- Análisis de grosor en múltiples puntos
- Métricas de forma (curvatura, área)
- Estandarización de orientación AC/PC

### Salidas

| Archivo | Descripción |
|---------|-------------|
| `cc_segmentation.mgz` | Segmentación del cuerpo calloso |
| `cc_thickness.csv` | Medidas de grosor |
| `cc_shape_metrics.json` | Métricas de forma |
| `orient_volume.lta` | Transformación de orientación |

### Opciones

```bash
--no_cc               # Desactivar este módulo
```

### Requisitos
- Requiere salida de `asegdkt`
- Imagen conformada (orig.mgz)

---

## CerebNet (cereb)

### Descripción
CerebNet proporciona sub-segmentación detallada del cerebelo, incluyendo la delineación de sustancia blanca y gris cerebelar.

### Arquitectura
- Red CNN 3D especializada
- Entrenada específicamente en estructuras cerebelares
- Resolución fija de 1mm (remuestreo automático)

### Salidas

| Archivo | Descripción |
|---------|-------------|
| `cerebellum.CerebNet.nii.gz` | Segmentación cerebelar detallada |
| `stats/cerebellum.stats` | Estadísticas volumétricas |

### Regiones Segmentadas
- Corteza cerebelar (lobules I-X)
- Sustancia blanca cerebelar
- Núcleos profundos
- Vermis

### Opciones

```bash
--no_cereb            # Desactivar este módulo
--cereb_segfile       # Ruta personalizada para salida
```

### Limitaciones
- No soporta alta resolución nativa
- Imágenes se remuestrean a 1mm

---

## HypVINN (hypothal)

### Descripción
HypVINN realiza la sub-segmentación del hipotálamo y estructuras adyacentes, con soporte opcional para imágenes T2-weighted.

### Arquitectura
- Puede usar solo T1w o T1w + T2w
- Registro automático de T2w a T1w
- Soporte para alta resolución (0.7mm)

### Salidas

| Archivo | Descripción |
|---------|-------------|
| `hypothalamus.HypVINN.nii.gz` | Segmentación hipotalámica |
| `stats/hypothalamus.stats` | Estadísticas de volumen |

### Estructuras Segmentadas
- Núcleos hipotalámicos
- 3er ventrículo
- Cuerpo mamilar
- Fórnix
- Tractos ópticos

### Opciones

```bash
--no_hypothal         # Desactivar este módulo
--t2 <path>           # Imagen T2w adicional
--reg_mode <mode>     # Modo de registro T2w→T1w
```

### Modos de Registro (--reg_mode)
- `coreg`: Co-registro rígido
- `robust`: Registro robusto (recomendado)
- `none`: Sin registro (imágenes ya alineadas)

---

## Recon-Surf (superficie)

### Descripción
El pipeline de reconstrucción de superficie genera mallas corticales, mapas de grosor y estadísticas por ROI.

### Fases

1. **Extracción de superficie**
   - Superficie pial
   - Superficie white matter
   - Inflación

2. **Esferización**
   - Mapeo a esfera
   - Registro al atlas

3. **Parcelación**
   - Mapeo de etiquetas DKT
   - Estadísticas por región

### Salidas

| Directorio/Archivo | Descripción |
|-------------------|-------------|
| `surf/lh.white` | Superficie WM hemisferio izquierdo |
| `surf/lh.pial` | Superficie pial hemisferio izquierdo |
| `surf/lh.thickness` | Mapa de grosor |
| `surf/lh.sphere.reg` | Registro esférico |
| `label/lh.aparc.DKTatlas.annot` | Parcelación cortical |
| `stats/lh.aparc.DKTatlas.stats` | Estadísticas por región |

### Opciones

```bash
--surf_only           # Solo ejecutar superficie
--no_surfreg          # Omitir registro esférico
--no_fs_T1            # Omitir generación de T1.mgz
--fstess              # Usar mri_tesselate (similar a FS)
--fsqsphere           # Usar esferización de FS
--fsaparc             # Usar parcelación de FS
--threads <N>         # Threads para superficie
```

### Requisitos
- Licencia de FreeSurfer
- Salidas de `asegdkt` y `cc`

---

## Flags Globales

### Entrada/Salida

```bash
--t1 <path>           # Imagen T1w de entrada (requerido)
--sd <path>           # Directorio de subjects (requerido)
--sid <name>          # ID del sujeto (requerido)
--fs_license <path>   # Licencia FreeSurfer (requerido para superficie)
```

### Procesamiento

```bash
--threads <N>         # Número de threads
--3T                  # Usar atlas 3T (recomendado para 3T)
--vox_size <size>     # Tamaño de voxel (min, o valor 0.7-1.0)
```

### Dispositivo

```bash
--device <dev>        # auto, cpu, cuda, cuda:0, mps
--viewagg_device <dev># Dispositivo para agregación de vistas
```

### Módulos

```bash
--seg_only            # Solo segmentación
--surf_only           # Solo superficie
--no_asegdkt          # Desactivar FastSurferVINN
--no_cc               # Desactivar CorpusCallosum
--no_cereb            # Desactivar CerebNet
--no_hypothal         # Desactivar HypVINN
```

---

## Combinaciones Recomendadas

### Análisis Volumétrico Rápido
```bash
--seg_only --no_cereb --no_hypothal
```
Tiempo: ~3 minutos

### Análisis Completo sin Superficie
```bash
--seg_only
```
Tiempo: ~5 minutos

### Pipeline Completo
```bash
# Sin flags adicionales
```
Tiempo: ~65-95 minutos

### Solo Cerebelo
```bash
--seg_only --no_hypothal
```
Tiempo: ~5 minutos

---

## Troubleshooting

### Error: "Out of GPU memory"
```bash
--viewagg_device cpu  # Mover agregación a CPU
# o
--device cpu          # Usar solo CPU
```

### Error: "FreeSurfer license not found"
```bash
--fs_license /path/to/license.txt
```

### Resultados de baja calidad
- Verificar calidad de imagen de entrada
- Verificar resolución (0.7-1mm recomendado)
- Considerar `--no_biasfield` si hay artefactos

### Procesamiento lento
- Usar GPU si está disponible
- Aumentar threads: `--threads 8`
- Para múltiples sujetos, procesar en paralelo
