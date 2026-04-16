# Triunfo — Spec-19 Agente Claude Vision (Anthropic SDK) v1.0
# Version: 1.0
# Fecha: 2026-04-16
# Estado: Pendiente

## Objetivo
Implementar `ClaudeVisionAgent`, agente de extracción multimodal que usa `claude-sonnet-4-6` via Anthropic SDK para procesar imágenes de facturas directamente. Corre en paralelo con los agentes Gemini en el orquestador de imagen (Spec-20). Usa prompt caching en el system prompt para reducir latencia y costo en procesamiento repetitivo de facturas.

## Ubicación
`src/agents/claude_vision.py`

## Clase

```
class ClaudeVisionAgent(BaseAgent):
    agent_id = "claude-vision"
    timeout_ms = 30000  # CLAUDE_VISION_TIMEOUT
```

## Criterio de aceptación

### Inicialización
- [ ] Hereda de `BaseAgent` (mismo contrato de interface que los agentes existentes de Spec-02)
- [ ] Instancia `anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)`
- [ ] Lee `CLAUDE_VISION_MODEL` (default: `claude-sonnet-4-6`) al inicializar

### Llamada a la API
- [ ] Envía la imagen como bloque `image` con `type: base64`, `media_type: image/jpeg` y `data: {base64}` dentro del array `content` del mensaje `user`
- [ ] El `system` prompt viene de `SYSTEM_PROMPT_FASE1` (Spec-18) con `cache_control: {"type": "ephemeral"}` activado
- [ ] Usa `max_tokens=2048` para el output de Fase 1
- [ ] Incluye el schema JSON de Fase 1 (Spec-18) al final del system prompt vía `inject_schema()`
- [ ] Solicita respuesta JSON estructurada con instrucción explícita en el prompt (Anthropic no tiene `response_mime_type` nativo — la instrucción está en el system prompt)

### Manejo de respuesta
- [ ] Parsea el texto del primer `ContentBlock` del response como JSON
- [ ] Si el parse falla → retry una vez con backoff de 2s
- [ ] Si el segundo parse falla → `AgentStatus.FAILED` con `error_detail: "invalid_json_response"`
- [ ] Mapea el JSON de Fase 1 al modelo `AgentOutput` (Spec-03), campo a campo:
  - `totales.total` → `fields.total_amount`
  - `emisor.razon_social` → `fields.supplier_name`
  - `emisor.cuit` → `fields.supplier_cuit`
  - `metadatos.tipo_comprobante` + letra → `fields.invoice_type`
  - `metadatos.punto_venta` + `metadatos.numero_comprobante` → `fields.invoice_number`
  - `metadatos.fecha_emision` → `fields.invoice_date`
  - `metadatos.fecha_vencimiento` → `fields.due_date`
  - `metadatos.moneda` → `fields.currency`
  - `totales.iva_21 + iva_105 + iva_27` (suma) → `fields.vat_amount`
  - `metadatos.cae` → `fields.cae`
  - `metadatos.vencimiento_cae` → `fields.cae_due_date`
- [ ] Confidence por campo:
  - `1.0` si el valor está presente y no nulo en el JSON de Fase 1
  - `0.0` si el valor es null
  - (No hay confidence explícita de Claude → usar presencia/ausencia como proxy)

### Retry y timeouts
- [ ] Retry: 1 reintento con backoff de 2s en errores HTTP 429 y 529 (overloaded)
- [ ] No reintentar en errores 400 (bad request) ni 401 (auth)
- [ ] Timeout de `CLAUDE_VISION_TIMEOUT` segundos → `AgentStatus.TIMEOUT`

### Metadata en AgentOutput
- [ ] `metadata.model_version` = `claude-sonnet-4-6`
- [ ] `metadata.processing_region` = `"anthropic-cloud"`
- [ ] `metadata.cache_hit` = True/False (leer del response header `anthropic-cache-read-input-tokens > 0`)
- [ ] `metadata.input_tokens` = tokens usados (incluye imagen)
- [ ] `metadata.output_tokens` = tokens del output

### Tests
- [ ] Test: factura Edenor (imagen JPEG) → `supplier_name`, `total_amount`, `invoice_date` no null
- [ ] Test: imagen en blanco (ya rechazada por Spec-17, pero si llega) → `AgentStatus.FAILED`
- [ ] Test: respuesta JSON inválida del modelo → retry → si persiste, `AgentStatus.FAILED`
- [ ] Test: timeout de 30s → `AgentStatus.TIMEOUT`
- [ ] Test: `metadata.cache_hit=True` en segunda llamada con mismo system prompt (requiere credenciales reales)

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | API key de Anthropic (obligatorio) |
| `CLAUDE_VISION_MODEL` | `claude-sonnet-4-6` | Model ID |
| `CLAUDE_VISION_TIMEOUT` | `30` | Timeout en segundos |
| `CLAUDE_MAX_TOKENS` | `2048` | Max tokens para output de extracción |

## Prompt caching

El system prompt de Fase 1 (Spec-18) es el mismo para cada factura. Al marcarlo con `cache_control: ephemeral`:
- Primera llamada: se cachea (cache miss normal)
- Llamadas siguientes dentro de 5 min: cache hit — reducción de ~90% en tokens de input del system prompt
- Beneficio estimado: el system prompt de Fase 1 tiene ~800 tokens. Con caching, el costo de input por factura baja de ~800+imagen a ~imagen solamente.

## Dependencias
- Spec-17 (imagen ya preprocesada antes de llegar a este agente)
- Spec-18 (prompts: `SYSTEM_PROMPT_FASE1`, `build_fase1_messages`, `inject_schema`)
- Spec-03 (modelo `AgentOutput`)
- `anthropic` SDK (agregar a `requirements.txt`)

## Out of scope
- Fase 2 (mapeo SAP): la ejecuta el orquestador (Spec-20) sobre el resultado conciliado, no cada agente individualmente
- Procesamiento de PDF: este agente solo recibe imágenes JPEG preprocesadas (Spec-17)
