# Triunfo — Spec-13 Agente Gemini 2.0 Flash (Vertex AI) v1.0
# Version: 1.0
# Fecha: 2026-04-14
# Estado: Pendiente

## Objetivo
Implementar `GeminiFlashAgent`, el primer agente del trío paralelo de Vertex AI. Usa `gemini-2.0-flash` para extraer campos de facturas argentinas via vision multimodal. Es el modelo equilibrado del grupo: buena precisión a velocidad razonable.

## Ubicación
`src/agents/vertex/gemini_flash.py`

## Clase
```python
class GeminiFlashAgent(BaseAgent):
    agent_id = "gemini-flash"
    timeout_ms = 30000  # VERTEX_TIMEOUT_FLASH
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
- [ ] Retry: 1 reintento con backoff en errores 429 / 500
- [ ] `metadata.model_version = "gemini-2.0-flash"`
- [ ] `metadata.processing_region` = valor de `VERTEX_AI_LOCATION`
- [ ] Test: factura Edenor → `supplier_name`, `total_amount`, `invoice_date` no null
- [ ] Test: timeout de 30s → `AgentStatus.TIMEOUT`

## Campos a extraer (Spec-03)
`supplier_name`, `supplier_cuit`, `invoice_type`, `invoice_number`, `invoice_date`,
`due_date`, `currency`, `net_amount`, `vat_amount`, `total_amount`, `cae`, `cae_due_date`

## Variables de entorno
| Variable | Default | Descripción |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | — | ID del proyecto GCP |
| `VERTEX_AI_LOCATION` | `us-central1` | Región de Vertex AI |
| `GEMINI_FLASH_MODEL` | `gemini-2.0-flash` | Model ID |
| `VERTEX_TIMEOUT_FLASH` | `30` | Timeout en segundos |
