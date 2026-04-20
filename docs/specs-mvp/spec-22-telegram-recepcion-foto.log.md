# Spec-22: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | 2026-04-20 |
| Duración estimada | ~20 min |
| Agente | claude-sonnet-4-6 |

## Secuencia de pasos

1. Creado `src/telegram_bot/downloader.py` con `download_telegram_file`, `TelegramDownloadError`, `SUPPORTED_MIME_TYPES`
2. Creado `src/telegram_bot/handlers.py` con `on_photo`, `on_document`, `_process_and_respond` (helper privado que evita duplicación entre los dos handlers)
3. Instalado `python-telegram-bot>=20.7` en el venv del proyecto (`D:/poc-triunfo/.venv`); no estaba instalado a pesar de estar en requirements.txt
4. Verificado: 50/50 tests pasan

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| Helper `_process_and_respond` privado | `on_photo` y `on_document` comparten 100% del flujo desde el download en adelante; extraer evita duplicación y es correcto para el MVP |
| `_get_pipeline()` lazy singleton en handlers.py | Evita importar `api.main._pipeline` (src no debe importar api); un singleton en módulo es suficiente para el MVP |
| Verificar tamaño antes de descargar (vía `photo.file_size`) | Para fotos, Telegram provee el tamaño antes de descargar; permite rechazo sin consumir ancho de banda |
| PDF incluido en `SUPPORTED_MIME_TYPES` | El pipeline ya soporta `application/pdf`; era un gap vs `/upload`; alineado con Spec-22 v1.1 |

## Errores y resoluciones

| Error | Causa | Resolución |
|-------|-------|------------|
| `ModuleNotFoundError: No module named 'telegram'` al verificar imports | `python-telegram-bot` no estaba instalado en el venv del proyecto aunque estaba en `requirements.txt` | Instalado con `.venv/Scripts/python.exe -m pip install "python-telegram-bot>=20.7"` |

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| Handlers de foto y documento en archivos separados | Spec los describe por separado pero no fuerza archivos distintos | Ambos en `handlers.py` junto con los comandos (Spec-24); todo en un módulo reduce complejidad de imports |

## Pre-requisitos descubiertos

- `python-telegram-bot` no instalado en el venv; necesario instalarlo manualmente además de estar en requirements.txt
