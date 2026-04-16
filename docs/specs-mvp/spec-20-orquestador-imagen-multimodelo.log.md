# Spec-20: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-16 |
| Duración estimada | ~30 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Implementado `src/agents/image_orchestrator.py` con `ImageOrchestrator`
2. Actualizado `src/pipeline/processor.py`:
   - Importado `ImageOrchestrator`
   - Agregado parámetro `mime_type` a `Pipeline.process()`
   - Inferencia de `mime_type` desde extensión del `file_name` si no se provee
   - Agregado flag `USE_IMAGE_ORCHESTRATOR` para activación opcional
   - Implementado método privado `_process_image()` como rama alternativa
3. Actualizado `requirements.txt` con `anthropic` y `google-cloud-aiplatform`
4. Verificado: 50/50 tests pasan sin cambios

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| Flag `USE_IMAGE_ORCHESTRATOR=true` | Sin credenciales los agentes fallan; el flag protege el flujo mock existente para tests y demos. Se activa cuando las credenciales están disponibles |
| Conciliación ponderada propia en `ImageOrchestrator` | El `Conciliator` existente (Spec-04) trabaja con `Dict[str, AgentOutput]` pero el orquestador de imagen necesita weights por modelo. Se implementa conciliación interna, compatible con el contrato del Conciliator |
| `run_fase2=False` por defecto en `run_sync` | Fase 2 (SAP mapping) consume una llamada extra a Claude; se activa solo cuando se aprueba el documento, no en el pipeline principal |
| `agent_outputs_from_result()` como método público | Permite a processor.py convertir el `OrchestratorResult` al formato `Dict[str, AgentOutput]` que espera el `DocumentResult` |

## Errores y resoluciones

| Error | Causa | Resolución |
|-------|-------|------------|
| 5 tests de pipeline fallaban | `mime_type` inferido como `image/jpeg` para todos los `.jpg` → activaba el orquestador → sin credenciales → `AUTO_REJECT` | Agregado flag `USE_IMAGE_ORCHESTRATOR` que por defecto es `false`; tests usan el flujo mock anterior |

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `OrchestratorResult` con dataclass | Spec describe campos | Implementado como `@dataclass` en Python; compatible |
| Fase 2 ejecutada tras conciliación | Spec lo describe como parte del flujo | `run_fase2=False` por defecto; Fase 2 opcional para no consumir créditos en cada llamada del POC |

## Pre-requisitos descubiertos

- `google-cloud-aiplatform` no estaba en `requirements.txt` → agregado
