# Triunfo — Spec-03 Contrato de Datos v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Entrada (ingesta)
```json
{
  "document_id": "uuid-v4",
  "sede_id": "demo-001",
  "source_channel": "web",
  "uploaded_by": "user@empresa.com",
  "uploaded_at": "2026-04-14T10:30:00Z",
  "mime_type": "image/jpeg",
  "gcs_uri": "gs://triunfo-demo/2026/04/14/uuid.jpg",
  "file_size_bytes": 245623,
  "file_name": "factura_edenor_abril.jpg"
}
```

## Estados del documento
- INGESTED: documento cargado
- CLASSIFIED: categoría y proveedor detectados
- PROCESSING: extracción en ejecución
- EXTRACTED: datos extraídos por agentes
- VALIDATED: validaciones completadas
- CONCILIATED: conciliación finalizada
- ROUTED: enrutado a AUTO_APPROVE / HITL_STANDARD / HITL_PRIORITY / AUTO_REJECT

## Salida por agente (estándar)
```json
{
  "document_id": "uuid-v4",
  "agent_id": "docai|tesseract|vertex|classifier|validator",
  "status": "SUCCESS|TIMEOUT|FAILED",
  "duration_ms": 1200,
  "fields": {
    "provider_name": {"value": "Edenor", "confidence": 0.96},
    "issue_date": {"value": "2026-03-01", "confidence": 0.90},
    "total_amount": {"value": 12345.67, "confidence": 0.94},
    "reference_number": {"value": "0001-00012345", "confidence": 0.88},
    "due_date": {"value": null, "confidence": 0.0}
  },
  "raw_text": "...",
  "metadata": {
    "model_version": "docai-2024-01",
    "processing_region": "us",
    "field_count": 4,
    "fields_with_confidence_gt_0_85": 3
  }
}
```

## Salida conciliada (Paso final)
```json
{
  "document_id": "uuid-v4",
  "status": "ROUTED",
  "category": "SERVICIOS",
  "provider": "Edenor",
  "confidence_score": 0.92,
  "extracted_fields": {
    "provider_name": {
      "value": "Edenor",
      "confidence": 0.96,
      "source": "majority",
      "sources_detail": {
        "docai": {"value": "Edenor", "confidence": 0.96},
        "tesseract": {"value": "EDENOR", "confidence": 0.88},
        "vertex": {"value": "Edenor", "confidence": 0.94}
      }
    },
    "issue_date": {
      "value": "2026-03-01",
      "confidence": 0.90,
      "source": "majority"
    },
    "total_amount": {
      "value": 12345.67,
      "confidence": 0.94,
      "source": "majority"
    },
    "reference_number": {
      "value": "0001-00012345",
      "confidence": 0.88,
      "source": "majority"
    }
  },
  "validation": {
    "is_consistent": true,
    "errors": [],
    "warnings": ["Low confidence on reference_number (0.88)"]
  },
  "routing": "AUTO_APPROVE",
  "processing_summary": {
    "total_duration_ms": 3450,
    "stages": [
      {"name": "classification", "duration_ms": 800, "status": "SUCCESS"},
      {"name": "docai", "duration_ms": 1200, "status": "SUCCESS"},
      {"name": "tesseract", "duration_ms": 400, "status": "SUCCESS"},
      {"name": "vertex", "duration_ms": 0, "status": "SKIPPED"},
      {"name": "validation", "duration_ms": 250, "status": "SUCCESS"},
      {"name": "conciliation", "duration_ms": 150, "status": "SUCCESS"}
    ],
    "models_used": ["docai", "tesseract"],
    "missing_fields": ["due_date", "period_start", "period_end"]
  }
}
```

## Para mostrar en UI (datos extraídos)
- Tabla resumen: campo, valor extraído, confidence general, fuente (agente)
- Tabla detalle por agente: mostrar qué extrajo cada uno
- Warnings: campos con baja confidence o validaciones fallidas
- Timeline: duración por etapa y modelo
- Métricas: modelos usados, skip reasons, confidence distribution
