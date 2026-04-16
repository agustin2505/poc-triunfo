# Triunfo — Spec-17 Preprocesamiento de Imágenes de Entrada v1.0
# Version: 1.0
# Fecha: 2026-04-16
# Estado: Pendiente

## Objetivo
Implementar `ImagePreprocessor`, utilidad que valida y normaliza imágenes de facturas antes de enviarlas a los agentes multimodales. Garantiza que las imágenes cumplan los requisitos de formato, tamaño y calidad mínimos para las APIs de Vertex AI y Anthropic.

## Ubicación
`src/utils/image_preprocessor.py`

## Contrato de entrada/salida

### Input
- `source`: path local (str) o bytes crudos (bytes) de la imagen
- `mime_type`: tipo MIME declarado por el uploader (`image/jpeg`, `image/png`, etc.)

### Output: `ProcessedImage`
```
ProcessedImage:
  image_bytes: bytes          # imagen final lista para enviar a APIs
  image_base64: str           # mismo contenido, codificado en base64
  mime_type: str              # siempre "image/jpeg" después del preprocesamiento
  width_px: int
  height_px: int
  size_bytes: int
  was_resized: bool
  was_rotated: bool           # True si se corrigió rotación EXIF
  was_converted: bool         # True si el formato original no era JPEG
  quality_score: float        # 0.0-1.0, estimación de legibilidad
```

## Formatos aceptados

| Formato original | Acción |
|---|---|
| JPEG | Sin conversión |
| PNG | Convertir a JPEG calidad 92 |
| WEBP | Convertir a JPEG calidad 92 |
| TIFF | Convertir a JPEG calidad 92 |
| Cualquier otro | Rechazar con `ImageFormatError` |

## Validaciones (rechazo inmediato si falla)

| Condición | Error |
|---|---|
| Archivo corrupto / no decodificable | `ImageCorruptError` |
| Dimensiones < 300 × 300 px | `ImageTooSmallError` |
| Tamaño > 20 MB | `ImageTooLargeError` |
| >98% píxeles con valor uniforme (negro/blanco total) | `ImageBlankError` |

## Transformaciones automáticas (sin error, solo flags)

| Condición | Acción |
|---|---|
| Tamaño > 4 MB tras conversión | Resize proporcional hasta ≤ 4 MB |
| Metadato EXIF `Orientation` != 1 | Rotar imagen para corregir orientación |

## Quality score (estimación interna, no bloquea el pipeline)

- Se calcula como: `1.0 - (ratio de píxeles uniformes)` sobre una muestra del centro de la imagen
- Score < 0.15 → `quality_score` se incluye en los metadatos del `AgentOutput` como advertencia
- Score < 0.05 → `ImageBlankError` (capturado por validación de píxeles uniformes)
- **No aplicar OCR, no aplicar mejora de contraste, no aplicar sharpening** — los modelos multimodales procesan la imagen directamente

## Criterio de aceptación

- [ ] `ImagePreprocessor.process(source, mime_type) -> ProcessedImage` implementado
- [ ] Acepta path (str) y bytes como `source`
- [ ] Convierte PNG, WEBP, TIFF a JPEG calidad 92
- [ ] Rechaza archivos corruptos con `ImageCorruptError`
- [ ] Rechaza imágenes < 300×300 px con `ImageTooSmallError`
- [ ] Rechaza imágenes > 20 MB con `ImageTooLargeError`
- [ ] Rechaza imágenes en blanco/negro total con `ImageBlankError`
- [ ] Resize proporcional a ≤ 4 MB si el archivo excede ese límite
- [ ] Corrige rotación EXIF y setea `was_rotated=True`
- [ ] `quality_score` calculado en todos los outputs exitosos
- [ ] Test: JPEG válido → sin conversión, `was_converted=False`
- [ ] Test: PNG 8 MB → convertido a JPEG, `was_resized=True`, tamaño final ≤ 4 MB
- [ ] Test: imagen de 200×200 px → `ImageTooSmallError`
- [ ] Test: imagen negra 100% → `ImageBlankError`
- [ ] Test: imagen con EXIF rotation 90° → `was_rotated=True`, imagen correctamente orientada

## Dependencias
- `Pillow` (ya en requirements.txt)
- No requiere modelos de ML ni credenciales de nube

## Out of scope
- Detección de desenfoque (blur detection): queda para spec futura si la precisión lo justifica
- Deskewing / corrección de perspectiva: fuera del MVP de imagen
- Ajuste automático de brillo/contraste: los modelos multimodales manejan esto mejor que heurísticas
