# Spec-23: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-20 |
| Duración estimada | ~15 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Creado `src/telegram_bot/formatter.py` con `format_result_message`, `format_low_confidence_message`, `format_error_message`, helpers `_fmt_amount` y `_fmt_field`
2. Agregado `on_result` y `_generate_pdf` en `handlers.py` (mismo archivo que Spec-22)
3. Verificado: 50/50 tests pasan

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| `parse_mode="HTML"` en todos los mensajes | Evita escaping de caracteres especiales que aparecen en montos y fechas argentinas (`$`, `.`, `,`, paréntesis) |
| Branching sobre `result.routing` (enum) | El pipeline ya determina el routing; el bot no recalcula desde `confidence_score`; corrección de la spec original v1.0 |
| Fallback a texto plano si PDF falla | El PDF es un complemento; si `generate_result_pdf` lanza excepción, el usuario igual recibe el resumen |
| Caption > 1024 chars: doc sin caption + mensaje separado | Límite de Telegram; detectado y manejado explícitamente |
| Formateo es-AR con replace en cadena | Evita dependencia de `locale` (compleja en Windows); suficiente para MVP |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `on_result(chat_id, document_id, result, bot)` con 4 args | Spec original usaba `document_id` separado | Implementado como `on_result(chat_id, result, bot)` — `result.document_id` ya lo contiene; menos duplicación |

## Pre-requisitos descubiertos

Ninguno.
