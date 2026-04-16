# Spec-13: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-16 |
| Duración estimada | ~15 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Creado `src/agents/vertex/` (nuevo directorio, no existía)
2. Creado `src/agents/vertex/prompts.py` como re-export de `prompts_imagen.py` (Spec-18)
3. Implementado `src/agents/vertex/gemini_flash.py` con `GeminiFlashAgent`
4. Verificado: import resuelve sin errores

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| Inicialización lazy (`_init_model`) | Permite instanciar el agente sin credenciales; falla con FAILED status al llamarlo, no al crear el Pipeline |
| Usa `build_prompts` de `prompts_imagen.py` vía `vertex/prompts.py` | Centraliza los prompts en un solo lugar (Spec-18), evita duplicación |
| Retry solo en `GoogleAPICallError` retryable (429/500/503) | No reintentar en errores de lógica (400) ni auth (401) |
| `temperature=0.0` en `GenerationConfig` | Extracción de datos → queremos outputs deterministas |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `timeout_ms = 30000` via `VERTEX_TIMEOUT_FLASH` | Env var mencionada pero el BaseAgent usa `timeout_ms` hardcodeado | Se mantiene en 30000 constante; env var se puede agregar en iteración futura |

## Pre-requisitos descubiertos

- `src/agents/vertex/prompts.py` necesitaba existir antes que el agente → implementado junto con Spec-18
