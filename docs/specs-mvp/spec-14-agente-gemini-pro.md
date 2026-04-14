# Triunfo — Spec-14 Agente Gemini 2.5 Pro (Vertex AI) v1.0
# Version: 1.0
# Fecha: 2026-04-14
# Estado: Pendiente

## Objetivo
Implementar `GeminiProAgent`, el agente de alta precisión del trío paralelo. Usa `gemini-2.5-pro-preview` para extraer campos de facturas argentinas. Optimizado para facturas con layouts complejos, texto manuscrito superpuesto o imágenes de baja calidad.

## Ubicación
`src/agents/vertex/gemini_pro.py`

## Clase
```python
class GeminiProAgent(BaseAgent):
    agent_id = "gemini-pro"
    timeout_ms = 90000  # VERTEX_TIMEOUT_PRO
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
- [ ] Retry: 2 reintentos con backoff exponencial en errores 429 / 500
- [ ] `metadata.model_version = "gemini-2.5-pro-preview"`
- [ ] `metadata.processing_region` = valor de `VERTEX_AI_LOCATION`
- [ ] Test: factura con calidad "poor" → `supplier_cuit` y `cae` con confidence >= 0.70
- [ ] Test: timeout de 90s → `AgentStatus.TIMEOUT`

## Campos a extraer (Spec-03)
`supplier_name`, `supplier_cuit`, `invoice_type`, `invoice_number`, `invoice_date`,
`due_date`, `currency`, `net_amount`, `vat_amount`, `total_amount`, `cae`, `cae_due_date`

## Variables de entorno
| Variable | Default | Descripción |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | — | ID del proyecto GCP |
| `VERTEX_AI_LOCATION` | `us-central1` | Región de Vertex AI |
| `GEMINI_PRO_MODEL` | `gemini-2.5-pro-preview` | Model ID |
| `VERTEX_TIMEOUT_PRO` | `90` | Timeout en segundos |

## Nota de performance
Es el modelo más lento del trío. El orquestador (Spec-16) puede usarlo como desempate cuando los modelos más rápidos ya respondieron pero tienen baja confidence o resultados contradictorios.
