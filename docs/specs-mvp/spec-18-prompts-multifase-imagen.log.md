# Spec-18: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-16 |
| Duración estimada | ~20 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Implementado `src/agents/prompts_imagen.py` con todos los prompts, schemas y builders
2. Implementado `src/agents/vertex/prompts.py` como re-export (Spec-16 lo importa)
3. Verificado que `map_fase1_to_agent_fields` genera campos compatibles con el Conciliador existente

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| Caracteres ASCII en los prompts (sin acentos) | Evita problemas de encoding en distintos entornos; los LLMs entienden igual |
| `map_fase1_to_agent_fields` en este módulo | Centraliza la lógica de traducción entre el schema rico de Fase 1 y los campos estándar del AgentOutput |
| Confidence por presencia/ausencia (1.0/0.0) | Los LLMs multimodales no proveen confidence por campo; usar presencia como proxy es honesto y compatible con el Conciliador |
| `parse_json_response` strip de bloques markdown | Claude y Gemini a veces envuelven el JSON en ```json``` aunque se les pida JSON puro; esta función lo maneja robustamente |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `build_fase1_messages_gemini` | Nombre en la spec | Se llama `build_fase1_parts_gemini` para ser más explícito sobre el retorno (son `Part`) |

## Pre-requisitos descubiertos

- Este módulo es la base de todos los nuevos agentes — se implementó primero aunque la spec es la 18
