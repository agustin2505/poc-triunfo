# Triunfo — Spec-21 Telegram Bot Setup y Ciclo de Vida v1.1
# Version: 1.1
# Fecha: 2026-04-20
# Estado: Pendiente

## Objetivo
Integrar un bot de Telegram al sistema Triunfo como canal de ingesta de facturas. El bot debe inicializarse junto con el servidor FastAPI via `lifespan`, soportar dos modos de operación (polling para desarrollo, webhook para producción), y exponer un endpoint `/telegram/webhook` en la API. Este spec cubre únicamente el setup, ciclo de vida y conectividad — no el procesamiento de imágenes ni la entrega de resultados.

## Ubicación
```
src/telegram_bot/__init__.py
src/telegram_bot/bot.py
api/routers/telegram.py
```

Cambios en archivos existentes:
- `api/main.py` — incluir router de Telegram y wiring del lifespan (ya tiene `lifespan` preparado)
- `.env` — nuevas variables (ver sección Variables de entorno)

> **Nota:** El módulo se llama `src/telegram_bot/` (no `src/telegram/`) para evitar colisión de nombres con el paquete PyPI `telegram` (python-telegram-bot).

## Dependencias externas
- `python-telegram-bot>=20.7` (async, compatible con asyncio de FastAPI)

## Arquitectura

```
FastAPI lifespan (api/main.py)
    ↓
TelegramBot.initialize(app)
    ├── TELEGRAM_MODE=webhook → registra POST /telegram/webhook, llama setWebhook en Telegram
    └── TELEGRAM_MODE=polling → lanza asyncio Task de polling en background

FastAPI shutdown (lifespan yield)
    └── TelegramBot.shutdown() → detiene polling o elimina webhook
```

## Flujo de inicialización

```
1. Leer TELEGRAM_BOT_TOKEN del entorno
2. Construir Application (python-telegram-bot) con ApplicationBuilder
3. Registrar handlers (ver Specs 22–24) — en orden: comandos primero, foto/documento después
4. Llamar application.initialize() + application.start()
5. if TELEGRAM_MODE == "webhook":
       a. Llamar await application.bot.set_webhook(
              TELEGRAM_WEBHOOK_URL + "/telegram/webhook",
              secret_token=TELEGRAM_WEBHOOK_SECRET
          )
       b. No iniciar updater (el webhook POST lo dispara externamente)
   elif TELEGRAM_MODE == "polling":
       a. Llamar await application.updater.start_polling()
       b. Lanzar como asyncio.create_task() para no bloquear el event loop
6. En FastAPI shutdown (lifespan): llamar application.updater.stop() + application.stop() + application.shutdown()
```

> **Importante:** No usar `application.run_polling()` — bloquea el event loop. Usar el patrón separado: `application.initialize()` → `application.start()` → `application.updater.start_polling()`.

## Criterios de aceptación

### Setup
- [ ] `src/telegram_bot/bot.py` — clase `TelegramBot` con métodos:
  - `initialize(app: FastAPI) -> None` — registra handlers y arranca según modo
  - `shutdown() -> None` — apaga limpiamente
  - `get_application() -> Application` — retorna la instancia para uso en handlers
- [ ] `src/telegram_bot/__init__.py` — exporta `TelegramBot`
- [ ] Si `TELEGRAM_BOT_TOKEN` no está en el entorno:
  - Log warning al arrancar
  - Bot no se inicializa, el resto del servidor funciona normalmente
  - `GET /health` sigue respondiendo 200

### Modo webhook
- [ ] `api/routers/telegram.py` — endpoint `POST /telegram/webhook`
  - Verifica el header `X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_WEBHOOK_SECRET`
  - Si el token no coincide: responder 403 (sin logs de error, es ruido normal)
  - Deserializa el body como `Update` de python-telegram-bot
  - Lo despacha a `application.process_update(update)`
  - Responde siempre 200 (Telegram requiere respuesta inmediata)
- [ ] El webhook se registra automáticamente en startup con `setWebhook` + `secret_token`
- [ ] Si `TELEGRAM_WEBHOOK_URL` está vacía en modo webhook: loguea error y no registra webhook

### Modo polling
- [ ] Se lanza como `asyncio.create_task()` dentro del lifespan de FastAPI
- [ ] Si la task falla con excepción: loguea error con traceback, no crashea el servidor

### Health check
- [ ] `GET /telegram/status` responde con:
  ```json
  {
    "mode": "polling | webhook | disabled",
    "connected": true | false,
    "bot_username": "@NombreDelBot | null",
    "webhook_url": "https://... | null",
    "last_update_at": "ISO timestamp | null"
  }
  ```

### Respuesta a `/start`
- [ ] El bot responde con mensaje de bienvenida al recibir `/start`:
  ```
  Bienvenido al sistema Triunfo de procesamiento de facturas.
  Enviame una foto de tu factura y te devuelvo los datos extraidos.
  Para mas informacion usa /ayuda.
  ```

## Variables de entorno

| Variable | Tipo | Default | Descripcion |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | str | `""` | Token del bot (BotFather) |
| `TELEGRAM_MODE` | str | `"polling"` | `polling` o `webhook` |
| `TELEGRAM_WEBHOOK_URL` | str | `""` | URL publica del servidor (solo en modo webhook) |
| `TELEGRAM_WEBHOOK_SECRET` | str | `""` | Secret token para validar POSTs al webhook |
| `TELEGRAM_ALLOWED_USERS` | str | `""` | Lista de user IDs separados por coma. Vacio = sin restriccion |

## Notas de implementacion
- El wiring del lifespan ya existe en `api/main.py`: busca `TELEGRAM_BOT_TOKEN` e instancia `TelegramBot` si está presente.
- Los handlers se registran en `bot.py` importando las funciones de `src/telegram_bot/handlers.py` (Specs 22–24).
- El orden de registro importa: `CommandHandler` de comandos antes que `MessageHandler` genérico.
- El control de acceso por `TELEGRAM_ALLOWED_USERS` se implementa como función utilitaria en `bot.py` y se llama al inicio de cada handler (Spec-24 lo detalla).
