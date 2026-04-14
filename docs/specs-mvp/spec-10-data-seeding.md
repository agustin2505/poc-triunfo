# Triunfo — Spec-10 Data Seeding Script v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Objetivo
Script Python para generar dataset de prueba con documentos realistas (Edenor, Metrogas, Factura Interna) con variabilidad en calidad.

## Estructura de datos generados

### Proporción: 10 docs por proveedor (total 30)
- Edenor: 10 (8 good, 1 medium, 1 poor)
- Metrogas: 10 (8 good, 1 medium, 1 poor)
- Factura Interna: 10 (8 good, 1 medium, 1 poor)

### Variabilidad de calidad
- Good (80%): imagen clara, formato estándar, todos los campos legibles
- Medium (10%): imagen con ruido, texto parcialmente borroso
- Poor (10%): imagen con mucho ruido, ángulo, baja iluminación

## Ubicaciones de almacenamiento
- Imágenes: `gs://triunfo-demo/golden-set/2026/04/[proveedor]/`
- Metadata: `./docs/specs-mvp/golden-set-manifest.json`
- Manifesto local: lista de document_id, provider, expected_values para validación

## Manifesto local (JSON)
```json
{
  "golden_set": [
    {
      "document_id": "uuid-edenor-001",
      "provider": "Edenor",
      "category": "SERVICIOS",
      "quality": "good",
      "expected_fields": {
        "provider_name": "Edenor",
        "issue_date": "2026-03-01",
        "total_amount": 12345.67,
        "reference_number": "0001-00012345",
        "meter_reading_start": "100000",
        "meter_reading_end": "100250"
      },
      "gcs_uri": "gs://triunfo-demo/golden-set/edenor/uuid-edenor-001.jpg",
      "uploaded_at": "2026-04-14T10:00:00Z"
    },
    ...
  ]
}
```

## Script (pseudocódigo)
```python
# script: ./scripts/generate-golden-set.py

def generate_edenor_invoice(quality="good"):
    # Generar imagen de factura Edenor realista
    # good: 300dpi, bien iluminada
    # medium: ruido Gaussian, slight blur
    # poor: rotation 15deg, low contrast
    return image_bytes

def generate_metrogas_invoice(quality="good"):
    # Similar para Metrogas

def generate_factura_interna_invoice(quality="good"):
    # Similar para Factura Interna

def main():
    manifesto = {"golden_set": []}
    
    for provider in ["edenor", "metrogas", "factura_interna"]:
        for i in range(10):
            quality = "good" if i < 8 else ("medium" if i == 8 else "poor")
            
            image = generate_invoice(provider, quality)
            doc_id = f"uuid-{provider}-{i:03d}"
            
            # Upload a GCS
            gcs_uri = upload_to_gcs(image, f"{provider}/{doc_id}.jpg")
            
            # Add to manifesto
            manifesto["golden_set"].append({
                "document_id": doc_id,
                "provider": provider,
                "quality": quality,
                "expected_fields": {...},
                "gcs_uri": gcs_uri
            })
    
    # Save manifesto
    save_manifesto(manifesto)
    print(f"Golden set creado: {len(manifesto['golden_set'])} documentos")
```

## Ejecución
```bash
python ./scripts/generate-golden-set.py --output ./docs/specs-mvp/golden-set-manifest.json
```

## Salida
- 30 imágenes en GCS
- Archivo local `golden-set-manifest.json` con metadata
- Log de generación con URLs