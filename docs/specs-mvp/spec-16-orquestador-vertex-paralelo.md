# Triunfo — Spec-16 Orquestador Vertex — Ejecución Paralela v1.0
# Version: 1.0
# Fecha: 2026-04-14
# Estado: Pendiente

## Objetivo
Implementar `VertexOrchestrator`, que lanza los 3 agentes Gemini (Spec-13, 14, 15) en paralelo via `asyncio.gather`, recolecta sus resultados y selecciona el mejor output para devolver al pipeline principal. Reemplaza al `VertexAgent` mock actual en `src/agents/agent_c_vertex.py`.

## Rol en el pipeline (Spec-02)
El orquestador ocupa el lugar del Agente C (Vertex fallback). Se invoca solo cuando Agente A (DocumentAI) **y** Agente B (Tesseract) ambos fallan.

```
Paso 3 del pipeline — antes:
  vertex_output = self.vertex.run(...)        # un solo modelo mock

Paso 3 del pipeline — después:
  vertex_output = self.vertex_orchestrator.run_sync(...)  # 3 modelos en paralelo
```

## Ubicación y estructura de archivos

```
src/agents/vertex/
├── __init__.py           # expone VertexOrchestrator
├── orchestrator.py       # este spec
├── gemini_flash_lite.py  # Spec-15
├── gemini_flash.py       # Spec-13
├── gemini_pro.py         # Spec-14
└── prompts.py            # prompts compartidos (ver abajo)
```

## Criterio de aceptación

### VertexOrchestrator
- [ ] `src/agents/vertex/orchestrator.py` — clase `VertexOrchestrator`
- [ ] Método público `run_sync(document_id, image_bytes, provider_id, quality)` → `AgentOutput`
  - Internamente ejecuta `asyncio.run(_run_parallel(...))`
  - Compatible con el pipeline síncrono actual (`processor.py`)
- [ ] Lanza los 3 agentes via `asyncio.gather(..., return_exceptions=True)`
- [ ] Timeout global configurable: `VERTEX_PARALLEL_TIMEOUT` (default 120s)
  - Si se alcanza el timeout: usa lo que haya llegado hasta ese momento
  - Si ninguno llegó: retorna `AgentStatus.TIMEOUT`
- [ ] Estrategia de selección configurable via `VERTEX_SELECTION_STRATEGY`:
  - `fastest_valid` — primer `SUCCESS` con >= 3 campos no null
  - `highest_confidence` — mayor promedio de confidence entre los exitosos
  - `majority` — mini-conciliación interna (mismo algoritmo de Spec-04) entre los 3 resultados
- [ ] `agent_id = "vertex-orchestrator"`
- [ ] `metadata.model_version = "vertex-orchestrator-v1"`
- [ ] `metadata.processing_region` = valor de `VERTEX_AI_LOCATION`
- [ ] Incluir en `AgentOutput.metadata` los datos del orquestador (ver formato abajo)

### prompts.py (compartido por los 3 agentes)
- [ ] `EXTRACTION_PROMPT_STEP1`: extrae todo el texto visible de la imagen
- [ ] `EXTRACTION_PROMPT_STEP2`: dado el texto, completa el JSON con el esquema de Spec-03
  - El JSON schema incluye todos los campos obligatorios y opcionales de Spec-03
  - Instrucción explícita de formato de fechas (ISO 8601), montos (decimal, sin símbolo) y CUIT (sin guiones)
- [ ] `build_prompts(image_bytes, mime_type) -> list[Part]`: construye la lista de partes para la llamada

### Integración en processor.py
- [ ] Reemplazar `from src.agents.agent_c_vertex import VertexAgent` por `from src.agents.vertex import VertexOrchestrator`
- [ ] Reemplazar instancia `self.vertex = VertexAgent()` por `self.vertex_orchestrator = VertexOrchestrator()`
- [ ] Reemplazar llamada en Paso 3 por `self.vertex_orchestrator.run_sync(...)`

## Metadata extendida del orquestador
```json
{
  "model_version": "vertex-orchestrator-v1",
  "processing_region": "us-central1",
  "orchestrator_strategy": "highest_confidence",
  "models_launched": ["gemini-flash-lite", "gemini-flash", "gemini-pro"],
  "models_succeeded": ["gemini-flash-lite", "gemini-flash"],
  "models_failed": ["gemini-pro"],
  "selected_model": "gemini-flash",
  "durations_ms": {
    "gemini-flash-lite": 3200,
    "gemini-flash": 8500,
    "gemini-pro": null
  }
}
```

## Tests
- [ ] 3 modelos exitosos: retorna el seleccionado según estrategia configurada
- [ ] 1 modelo falla: retorna el mejor de los 2 restantes sin error
- [ ] Todos fallan: retorna `AgentStatus.FAILED`
- [ ] Timeout global alcanzado con 1 exitoso: retorna ese resultado con `status=SUCCESS`
- [ ] Timeout global alcanzado con 0 exitosos: retorna `AgentStatus.TIMEOUT`
- [ ] Estrategia `majority`: resultado es la conciliación de los 3, no solo el mejor

## Variables de entorno
| Variable | Default | Descripción |
|---|---|---|
| `VERTEX_PARALLEL_TIMEOUT` | `120` | Timeout global en segundos |
| `VERTEX_SELECTION_STRATEGY` | `highest_confidence` | Estrategia de selección |
| Ver Spec-13, 14, 15 | — | Variables por modelo individual |
