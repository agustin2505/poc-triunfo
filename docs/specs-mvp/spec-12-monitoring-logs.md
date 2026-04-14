# Triunfo — Spec-12 Monitoring & Logs v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Logging

### Niveles y eventos principales
DEBUG: entrada/salida de funciones, parsing detalles
INFO: documento ingested, clasificado, validado, routed
WARNING: low confidence (< 0.85), validación warning, desviación numérica
ERROR: agente falla, validación crítica falla, conexión SAP falla
CRITICAL: documento rechazado, SAP mock error persistente

### Estructura de log por documento
```
timestamp | level | document_id | event | details
2026-04-14T12:30:45.123Z | INFO | uuid-001 | INGESTED | sede=demo-001, size=245KB
2026-04-14T12:30:46.001Z | INFO | uuid-001 | CLASSIFIED | category=SERVICIOS, provider=Edenor, confidence=0.94
2026-04-14T12:30:47.200Z | INFO | uuid-001 | DOCAI_SUCCESS | duration=1200ms, fields=4, confidence_avg=0.92
2026-04-14T12:30:47.600Z | INFO | uuid-001 | TESSERACT_SUCCESS | duration=400ms, fields=3, confidence_avg=0.85
2026-04-14T12:30:48.100Z | INFO | uuid-001 | VALIDATION_PASSED | errors=0, warnings=1
2026-04-14T12:30:48.250Z | INFO | uuid-001 | ROUTED | routing=AUTO_APPROVE, confidence_score=0.92
2026-04-14T12:30:49.100Z | INFO | uuid-001 | SAP_SUCCESS | sap_doc=4900001234, posting_date=2026-04-14
```

### Almacenamiento
- Cloud Logging (GCP Logs): logs en tiempo real
- Cloud Storage: rotación diaria, retención 90 días
- Local development: stdout + archivo ./logs/triunfo.log

## Monitoreo

### Dashboards principales (Stackdriver/Data Studio)

#### Dashboard 1: Pipeline Health
- Documentos procesados hoy (contador)
- Documentos por estado (AUTO_APPROVE, HITL, REJECT)
- STP rate (% AUTO_APPROVE)
- Latencia P50, P95, P99 (gráfico de línea)
- Error rate (%)

#### Dashboard 2: Modelo Metrics
- Uso por modelo (DocumentAI, Tesseract, Vertex): % de invocaciones
- Confidence distribution: histograma
- Fallback rate: % de documentos que requieren agente fallback
- Timeout rate: % de agentes que superan timeout
- Duración promedio por agente: tabla

#### Dashboard 3: Validaciones
- Validaciones fallidas: top 5 reglas que fallan
- Warnings por tipo: aritmética, duplicado, rango, formato
- Accuracy por proveedor: Edenor, Metrogas, Factura Interna

#### Dashboard 4: Routing Distribution
- Breakdown: AUTO_APPROVE % | HITL_STANDARD % | HITL_PRIORITY % | AUTO_REJECT %
- HITL queue depth (documentos esperando)
- Trending: cambios en distribución por día

### Alertas
- STP < 50%: alerta YELLOW
- Error rate > 5%: alerta RED
- Latencia P95 > 5s: alerta YELLOW
- Agente timeout rate > 10%: alerta RED
- SAP mock fallos > 20%: alerta RED

## Métricas por agente (instrumentación)

Cada agente exporta:
```python
{
  "agent_id": "docai|tesseract|vertex|classifier|validator",
  "invocations": 150,
  "successes": 145,
  "failures": 5,
  "success_rate": 0.9667,
  "timeouts": 2,
  "timeout_rate": 0.0133,
  "duration_ms_avg": 1200,
  "duration_ms_p95": 1800,
  "duration_ms_p99": 2100,
  "confidence_avg": 0.91,
  "confidence_min": 0.62,
  "confidence_max": 0.99
}
```

## Auditoría

### Logs de cambios (HITL feedback)
```
document_id | timestamp | user_id | field | old_value | new_value | reason
uuid-001 | 2026-04-14T13:00:00Z | user@emp.com | total_amount | 12345.67 | 12345.68 | OCR error correction
uuid-001 | 2026-04-14T13:00:15Z | user@emp.com | reference_number | 0001-00012344 | 0001-00012345 | typo correction
```

## Health check
- Endpoint: `GET /health`
- Respuesta:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-14T12:30:00Z",
  "components": {
    "gcs": "healthy",
    "sql": "healthy",
    "docai": "healthy",
    "vertex": "healthy",
    "sap_mock": "healthy"
  }
}
```

## Retención y privacidad
- Logs: 90 días (GCS), 30 días (Cloud Logging)
- Documentos: 180 días (GCS) - verificar GDPR/privacidad
- Masking: números de tarjeta, CUIT (si aparecen en logs)
