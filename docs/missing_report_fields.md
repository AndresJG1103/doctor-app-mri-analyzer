# Volumetry Report - Campos No Disponibles

Este documento lista los campos del reporte de ejemplo (`docs/example_report.pdf`) que **no están disponibles** en el output de FastSurfer/FreeSurfer y por lo tanto no pueden ser incluidos automáticamente en el reporte generado.

## Campos de Encabezado

| Campo | Descripción | Razón de ausencia |
|-------|-------------|-------------------|
| **Sex** | Sexo del paciente (Male/Female) | Debe ser proporcionado por el usuario al enviar el job |
| **Age** | Edad del paciente | Debe ser proporcionado por el usuario al enviar el job |
| **Scale Factor** | Factor de escala de la imagen | No calculado por FastSurfer |
| **SNR** | Signal-to-Noise Ratio | No calculado por FastSurfer |

## Campos de Segmentación de Tejidos

| Campo | Descripción | Razón de ausencia |
|-------|-------------|-------------------|
| **Abnormal Appearing White Matter** | Materia blanca con apariencia anormal | Requiere segmentación de lesiones (no incluida en FastSurfer estándar) |
| **Normal Appearing White Matter** | Materia blanca normal (diferenciada de anormal) | Sin segmentación de lesiones, se asume todo como "normal" |

## Campos de Estructuras Subcorticales

| Campo | Descripción | Razón de ausencia |
|-------|-------------|-------------------|
| **Basal Forebrain** | Estructuras del prosencéfalo basal | No incluido en la parcellation estándar de FastSurfer |

## Rangos de Referencia

| Campo | Descripción | Razón de ausencia |
|-------|-------------|-------------------|
| **[Min, Max]** valores de referencia | Rangos esperados (95%) según sexo y edad | Requiere base de datos normativa no disponible |
| **Highlighting en rojo** | Valores fuera de rangos normales | Depende de los rangos de referencia |

## Campos de Imágenes

| Campo | Descripción | Razón de ausencia |
|-------|-------------|-------------------|
| **Imágenes 3D de referencia** | Visualización 3D de la parcellation | Requiere renderizado 3D adicional (puede implementarse con VTK/Mayavi) |

## Recomendaciones para Implementación Futura

1. **Información del paciente (Sex, Age)**: Agregar campos opcionales al endpoint `/api/v1/mri/process` para capturar esta información al momento del upload.

2. **Rangos normativos**: Integrar base de datos normativa como:
   - ENIGMA normative data
   - VolBrain reference data
   - Datos propios de la institución

3. **Segmentación de lesiones**: Integrar herramientas de segmentación de lesiones como:
   - LST (Lesion Segmentation Toolbox)
   - SAMSEG de FreeSurfer

4. **Visualización 3D**: Implementar generación de imágenes 3D usando:
   - FreeSurfer's FreeView screenshots
   - Python VTK/Mayavi rendering
   - Nilearn plotting utilities

## Versión del Documento

- **Fecha**: 2026-03-01
- **Versión FastSurfer**: gpu-latest
- **Parcellation**: DKTatlas
