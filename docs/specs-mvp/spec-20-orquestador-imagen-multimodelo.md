# Triunfo — Spec-20 Orquestador Imagen Multi-Modelo v1.0
# Version: 1.0
# Fecha: 2026-04-16
# Estado: Pendiente

## Objetivo
Implementar `ImageOrchestrator`, que coordina la extracción desde imagen corriendo Claude Vision (Spec-19) y los agentes Gemini (Specs 13-15) en paralelo, reconcilia sus resultados (Fase 1), ejecuta el mapeo SAP (Fase 2) sobre el resultado conciliado, y decide el routing final (AUTO_APPROVE / HITL / AUTO_REJECT).

Reemplaza el rol del Agente C (Vertex fallback) en el pipeline actual: para documentos en formato imagen, el `ImageOrchestrator` ocupa el slot de extracción primaria — no es fallback, es la ruta principal.

## Ubicación
`src/agents/image_orchestrator.py`

## Rol en el pipeline (actualiza Spec-02)

```
Pipeline para documentos imagen (antes):
  A (DocumentAI) + B (Tesseract) → conciliate → E → SAP

Pipeline para documentos imagen (después):
  ImageOrchestrator → conciliate → Fase 2 (mapeo SAP) → E → routing
```

Los Agentes A (DocumentAI) y B (Tesseract) quedan como fallback opcionales para documentos donde el OCR estructurado sea más eficiente (ej: PDFs con texto seleccionable). El `ImageOrchestrator` se activa cuando `mime_type` es `image/*`.

## Flujo interno

```
[ProcessedImage desde Spec-17]
          ↓
[Fase 1 — Extracción Paralela]
  asyncio.gather con timeout IMAGEN_PARALLEL_TIMEOUT:
  ├── ClaudeVisionAgent (Spec-19)        → AgentOutput A
  ├── GeminiFlashLiteAgent (Spec-15)     → AgentOutput B
  ├── GeminiFlashAgent (Spec-13)         → AgentOutput C
  └── GeminiProAgent (Spec-14)           → AgentOutput D
          ↓
[Conciliación — algoritmo existente (Spec-04)]
  · Voto campo a campo con weights por modelo
  · Score de confianza por campo
          ↓
[Fase 2 — Mapeo SAP (Agent E via Claude)]
  · Toma el JSON conciliado de Fase 1
  · Llama a Claude con SYSTEM_PROMPT_FASE2 + USER_PROMPT_FASE2 (Spec-18)
  · Output: SAPPayload + trazabilidad
          ↓
[Thresholds de confianza → routing]
  · Score campos críticos >= THRESHOLD_CRITICO → AUTO_APPROVE
  · Score campos críticos <  THRESHOLD_CRITICO → HITL
  · Todos los modelos fallaron → AUTO_REJECT
```

## Criterio de aceptación

### Fase 1 — Extracción paralela
- [ ] `src/agents/image_orchestrator.py` — clase `ImageOrchestrator`
- [ ] Método público `run_sync(document_id, processed_image, provider_id) -> OrchestratorResult`
  - Internamente ejecuta `asyncio.run(_run_parallel(...))`
  - Compatible con el pipeline síncrono de `processor.py`
- [ ] Lanza los 4 agentes via `asyncio.gather(..., return_exceptions=True)`
- [ ] Timeout global `IMAGEN_PARALLEL_TIMEOUT` (default 120s):
  - Al alcanzarlo: usa los resultados que hayan llegado hasta ese momento
  - Si ninguno llegó: `OrchestratorStatus.TIMEOUT`
- [ ] Mínimo de agentes exitosos para continuar: `IMAGEN_MIN_AGENTS_OK` (default 1)
  - Si 0 agentes exitosos: `OrchestratorStatus.FAILED` → `AUTO_REJECT`

### Conciliación
- [ ] Reutiliza `Conciliator` de `src/conciliation/conciliator.py` (Spec-04) sin modificarlo
- [ ] Weights por modelo (configurable via variables de entorno, defaults en tabla abajo):

| Agente | Weight default |
|---|---|
| `claude-vision` | 0.35 |
| `gemini-flash` | 0.30 |
| `gemini-pro` | 0.25 |
| `gemini-flash-lite` | 0.10 |

- [ ] Campos críticos: `total_amount`, `supplier_cuit`, `invoice_date`, `invoice_number`
- [ ] Score de confianza por campo incluido en el resultado conciliado (igual que Spec-04)

### Fase 2 — Mapeo SAP
- [ ] Ejecuta Fase 2 usando `ClaudeVisionAgent` (o instancia separada del Anthropic SDK) con `SYSTEM_PROMPT_FASE2` (Spec-18)
- [ ] Input: JSON conciliado de Fase 1 serializado como string
- [ ] Output: `SAPPayload` (Spec-18 schema Fase 2)
- [ ] Si Fase 2 falla → `routing = HITL_PRIORITY`, incluir error en `advertencias`
- [ ] Fase 2 usa prompt caching (mismo mecanismo que Spec-19)

### Routing final
| Condición | Routing |
|---|---|
| Todos los campos críticos con confidence >= `THRESHOLD_CRITICO` (default 0.90) | `AUTO_APPROVE` |
| Al menos 1 campo crítico con confidence en [0.70, 0.90) | `HITL_STANDARD` |
| Al menos 1 campo crítico con confidence < 0.70 | `HITL_PRIORITY` |
| 0 agentes exitosos | `AUTO_REJECT` |

### Output: `OrchestratorResult`
```
OrchestratorResult:
  document_id: str
  status: OrchestratorStatus (SUCCESS | PARTIAL | TIMEOUT | FAILED)
  fase1_conciliado: dict            # campos conciliados con confidence
  fase2_sap_payload: dict | None
  routing: str                      # AUTO_APPROVE | HITL_STANDARD | HITL_PRIORITY | AUTO_REJECT
  confidence_score_global: float    # promedio de campos críticos
  models_launched: list[str]
  models_succeeded: list[str]
  models_failed: list[str]
  durations_ms: dict                # {agent_id: ms}
  fase2_trazabilidad: dict | None
  advertencias: list[str]
```

### Integración en processor.py
- [ ] Si `mime_type.startswith("image/")` → usar `ImageOrchestrator.run_sync()`
- [ ] Si `mime_type == "application/pdf"` → mantener flujo anterior (A + B + C)
- [ ] El routing output de `ImageOrchestrator` reemplaza al routing calculado por `Conciliator` directamente

### Tests
- [ ] 4 agentes exitosos: resultado conciliado incluye valores de los 4, routing correcto
- [ ] 1 agente falla: orquestador continúa con los 3 restantes sin error
- [ ] Todos fallan: `AUTO_REJECT`
- [ ] Timeout global con 2 exitosos: usa esos 2, marca los otros como `TIMEOUT`
- [ ] Campos críticos con confidence < 0.90 → `HITL`
- [ ] Fase 2 falla → routing es `HITL_PRIORITY` (no `AUTO_REJECT`)
- [ ] PDF input → NO usa `ImageOrchestrator` (flujo antiguo)

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `IMAGEN_PARALLEL_TIMEOUT` | `120` | Timeout global para los 4 agentes (segundos) |
| `IMAGEN_MIN_AGENTS_OK` | `1` | Mínimo agentes exitosos para no AUTO_REJECT |
| `THRESHOLD_CRITICO` | `0.90` | Confidence mínima en campos críticos para AUTO_APPROVE |
| `WEIGHT_CLAUDE` | `0.35` | Peso en conciliación para Claude Vision |
| `WEIGHT_GEMINI_FLASH` | `0.30` | Peso en conciliación para Gemini Flash |
| `WEIGHT_GEMINI_PRO` | `0.25` | Peso en conciliación para Gemini Pro |
| `WEIGHT_GEMINI_FLASH_LITE` | `0.10` | Peso en conciliación para Gemini Flash Lite |
| Ver Spec-13, 14, 15, 19 | — | Variables por modelo individual |

## Dependencias
- Spec-17 (imagen preprocesada como input)
- Spec-18 (prompts Fase 1 y Fase 2)
- Spec-19 (ClaudeVisionAgent)
- Spec-13, 14, 15 (agentes Gemini)
- Spec-04 (Conciliator reutilizado sin cambios)
- Spec-03 (AgentOutput y contratos de datos)

## Out of scope
- Procesamiento de PDFs con texto seleccionable: sigue con flujo A+B+C (Spec-02)
- Reentrenamiento o fine-tuning de modelos: fuera del scope del pipeline
- Cache persistente entre sesiones para los resultados: la caché de prompts la gestiona la API de Anthropic
