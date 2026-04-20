# Spec-24: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-20 |
| Duración estimada | ~15 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Agregado `check_access` como función utilitaria al inicio de `handlers.py`
2. Implementados `cmd_start`, `cmd_ayuda`, `cmd_estado`, `cmd_aprobar`, `cmd_rechazar` en `handlers.py`
3. Implementado `handle_inline_callback` con `query.answer()` al inicio y edición del teclado inline al final
4. Helper `_resolve_doc_id` que unifica la lógica de resolución del doc_id en todos los comandos
5. Verificado: 50/50 tests pasan

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| `store.approve/reject` como interfaz directa | La lógica está centralizada en `src/store.py`; los handlers solo propagan KeyError/ValueError como mensajes al usuario |
| `check_access` llama `query.answer()` antes de retornar en callbacks | PTB requiere que se responda al callback dentro de su TTL (30s); si el check falla, igual hay que responder |
| Alias `/help` registrado junto a `/ayuda` | BotFather autocompleta `/help`; usuarios esperan ese comando por convención Telegram |
| `_resolve_doc_id` helper privado | Los 3 comandos tienen la misma lógica de resolución; centralizar evita bugs de consistencia |
| `doc_id[:8]` en mensajes de confirmación | Los UUIDs completos son verbosos; mostrar 8 chars es suficiente para identificación visual |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| `check_access` como función separada | Spec la describe en `handlers.py` genéricamente | Implementada al inicio de `handlers.py`, antes de todos los otros handlers, como función reutilizable |
| Comandos en archivo separado | Spec-24 implica que es solo en `handlers.py` | Todo en `handlers.py`: specs 22+23+24 comparten el mismo módulo, lo que evita imports circulares y mantiene el módulo cohesivo |

## Pre-requisitos descubiertos

- `src/store.py` creado previamente como parte del refactor Spec-21; ya disponible con `approve`, `reject`, `is_approved`, `is_rejected`
