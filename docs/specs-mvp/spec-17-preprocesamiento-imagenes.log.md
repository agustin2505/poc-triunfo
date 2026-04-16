# Spec-17: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-16 |
| Duración estimada | ~20 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Creado directorio `src/utils/` (no existía)
2. Creado `src/utils/__init__.py`
3. Implementado `src/utils/image_preprocessor.py` con `ImagePreprocessor`
4. Verificado: import resuelve correctamente con Pillow disponible

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| `Image.open().verify()` + reabrir | Pillow invalida el objeto tras `verify()`, hay que reabrir para operar sobre él |
| Segunda pasada de compresión (quality=75) si aún > 4MB | Imágenes muy densas pueden no reducir suficiente con el primer resize; evita enviar archivos que excedan el límite de la API |
| `quality_score` via muestreo en región central (50×50 thumb) | Eficiente sin necesitar bibliotecas adicionales; el centro de la factura suele tener el texto más importante |
| `ImageOps.exif_transpose` con try/except | Algunas imágenes tienen EXIF malformado; no bloquear el proceso por un error en metadatos |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `score_calidad_estimado` en output | Spec usa ese nombre | Se llama `quality_score` en el dataclass (más pythónico); mismo concepto |

## Pre-requisitos descubiertos

- `Pillow` ya está en `requirements.txt` — no fue necesario agregarlo
