# Triunfo — Spec-15 Agente Gemini 2.5 Flash (Vertex AI) v1.0
# Version: 1.0
# Fecha: 2026-04-14
# Estado: Pendiente

## Objetivo
Implementar `GeminiFlashLiteAgent`, el agente de máxima velocidad del trío paralelo. Usa `gemini-2.5-flash` para extraer campos de facturas argentinas. Primer resultado disponible para el orquestador y referencia de latencia para la métrica P95 < 5s del MVP.

## Ubicación
`src/agents/vertex/gemini_flash_lite.py`

## Clase
```python
class GeminiFlashLiteAgent(BaseAgent):
    agent_id = "gemini-flash-lite"
    timeout_ms = 20000  # VERTEX_TIMEOUT_FLASH_LITE
```

## Criterio de aceptación
- [ ] Hereda de `BaseAgent` (mismo contrato que los agentes existentes)
- [ ] Usa `google-cloud-aiplatform` SDK — `vertexai.generative_models.GenerativeModel`
- [ ] Inicializa con `vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=VERTEX_AI_LOCATION)`
- [ ] Envía la imagen como bytes en base64 (`Part.from_data(image_bytes, mime_type)`)
- [ ] Ejecuta prompt en 2 pasos (ver Spec-16 `src/agents/vertex/prompts.py`):
  1. Extracción textual libre de la factura
  2. Mapeo al esquema de campos JSON
- [ ] Usa `response_mime_type="application/json"` para structured output
- [ ] Retorna `AgentOutput` con todos los campos de Spec-03
- [ ] Retry: 1 reintento con backoff en errores 429 / 500 (NO reintentar si es timeout)
- [ ] `metadata.model_version = "gemini-2.5-flash"`
- [ ] `metadata.processing_region` = valor de `VERTEX_AI_LOCATION`
- [ ] Test: factura Metrogas → `total_amount` e `invoice_date` no null
- [ ] Test: latencia promedio < 5s en 10 llamadas consecutivas
- [ ] Test: timeout de 20s → `AgentStatus.TIMEOUT`

## Campos a extraer (Spec-03)
`supplier_name`, `supplier_cuit`, `invoice_type`, `invoice_number`, `invoice_date`,
`due_date`, `currency`, `net_amount`, `vat_amount`, `total_amount`, `cae`, `cae_due_date`

## Variables de entorno
| Variable | Default | Descripción |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | — | ID del proyecto GCP |
| `VERTEX_AI_LOCATION` | `us-central1` | Región de Vertex AI |
| `GEMINI_FLASH_LITE_MODEL` | `gemini-2.5-flash` | Model ID |
| `VERTEX_TIMEOUT_FLASH_LITE` | `20` | Timeout en segundos |
