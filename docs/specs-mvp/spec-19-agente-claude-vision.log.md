# Spec-19: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-16 |
| Duración estimada | ~20 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Implementado `src/agents/claude_vision.py` con `ClaudeVisionAgent`
2. Agregado `anthropic>=0.40.0` a `requirements.txt`
3. Verificado: import resuelve sin errores (SDK no instalado aún → lazy init lo maneja)

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| `anthropic.Anthropic()` sync en lugar de `AsyncAnthropic` | El pipeline es síncrono; usar sync client es más simple y `ThreadPoolExecutor` en el orquestador provee paralelismo |
| `cache_control: {"type": "ephemeral"}` en el system prompt | Activa prompt caching de Anthropic; el system prompt de ~800 tokens se reutiliza entre llamadas dentro de una sesión (TTL 5 min) |
| Detección de cache hit via `cache_read_input_tokens > 0` | Es el único indicador disponible en el response de la API de Anthropic |
| Retry solo en 429 y 529 | 529 = "overloaded" es específico de Anthropic; ambos son transitorios y vale reintentar |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `AsyncAnthropic` | Spec especifica cliente async | Se usó sync `Anthropic()` para compatibilidad con el pipeline síncrono; el paralelismo lo da `ThreadPoolExecutor` en el orquestador |

## Pre-requisitos descubiertos

- `anthropic` SDK no estaba en `requirements.txt` → agregado
