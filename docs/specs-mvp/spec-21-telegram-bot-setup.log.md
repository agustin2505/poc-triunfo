# Spec-21: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-20 |
| Duración estimada | ~20 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Creado `src/telegram_bot/__init__.py` — exporta `TelegramBot`
2. Creado `src/telegram_bot/bot.py` — clase `TelegramBot` con `initialize`, `shutdown`, `get_application`, `_register_handlers`, `_setup_webhook`
3. Creado `api/routers/__init__.py` y `api/routers/telegram.py` — endpoints `POST /telegram/webhook` y `GET /telegram/status`
4. Actualizado `api/main.py`:
   - Lifespan guarda el bot en `app.state.telegram_bot` para acceso sin circular import
   - Incluido `telegram_router` via `app.include_router`
5. Actualizado `requirements.txt` con `python-telegram-bot>=20.7`
6. Verificado: 50/50 tests pasan

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| `app.state.telegram_bot` en lugar de importar `api.main._telegram_bot` en el router | Evita circular import entre `api.main` (que incluye el router) y `api/routers/telegram.py` |
| Módulo llamado `src/telegram_bot/` en lugar de `src/telegram/` | Evita colisión de nombre con el paquete PyPI `telegram` que usa python-telegram-bot |
| `updater.start_polling()` directo sin `asyncio.create_task` | En PTB v20, `start_polling()` es no-bloqueante: inicia tareas internas y retorna; no necesita wrapping adicional |
| Secret token validado en el router (no en el bot) | La responsabilidad HTTP es del router; el bot solo procesa updates ya validados |

## Errores y resoluciones

Ninguno.

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| Handler `_register_handlers` intenta import con try/except | Spec asumía que handlers podría no existir en Spec-21 | Se implementan todos los handlers en la misma sesión; no hace falta el try/except. Se mantiene la importación directa para claridad |

## Pre-requisitos descubiertos

- `api/routers/` no existía como directorio — creado con `__init__.py`
