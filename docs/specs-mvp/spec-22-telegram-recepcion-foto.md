# Triunfo — Spec-22 Telegram Recepción y Normalización de Foto v1.1
# Version: 1.1
# Fecha: 2026-04-20
# Estado: Done

## Objetivo
Manejar los mensajes de foto (y documentos de imagen/PDF) que el usuario envía al bot, descargar el archivo desde los servidores de Telegram, y disparar el procesamiento a través del pipeline existente. Este spec cubre el camino desde la recepción del mensaje hasta la llamada a `Pipeline.process()` y el guardado del resultado en el store.

## Ubicación
```
src/telegram_bot/handlers.py   — on_photo(), on_document()
src/telegram_bot/downloader.py — download_telegram_file()
```

Depende de: Spec-21 (bot inicializado), `src/pipeline/processor.py` (Pipeline), `src/store.py` (store compartido).

## Control de acceso
Antes de cualquier procesamiento, verificar si `TELEGRAM_ALLOWED_USERS` está configurado. Si el `update.effective_user.id` no está en la lista, responder "No tenés permiso para usar este bot." y retornar. Ver Spec-24 para la función utilitaria `check_access(update)`.

## Flujo

```
Usuario envía foto en Telegram
    ↓
handler on_photo(update, context) disparado
    ↓
check_access(update) — si falla: responder y retornar
    ↓
Responder inmediatamente: "Recibido. Procesando tu factura, aguarda un momento..."
    ↓
downloader.get_best_photo(update.message.photo)
    → update.message.photo es lista de PhotoSize ordenada de menor a mayor resolución
    → Tomar el último elemento (mayor calidad)
    ↓
downloader.download_telegram_file(file_id, bot) → bytes
    ↓
Ejecutar pipeline en executor (no bloquear event loop):
    loop.run_in_executor(None, _run_pipeline, image_bytes, chat_id)
    ↓
result = Pipeline().process(
    image_bytes=image_bytes,
    file_name=f"factura_{chat_id}_{timestamp}.jpg",
    mime_type="image/jpeg",
)
    ↓
store.save(result)
    ↓
context.user_data["last_document_id"] = result.document_id
    ↓
Llamar on_result(chat_id, result, context.bot) → ver Spec-23
```

## Firma correcta de Pipeline.process

```python
# src/pipeline/processor.py
result = pipeline.process(
    image_bytes=image_bytes,      # bytes descargados directamente
    file_name="factura.jpg",      # nombre descriptivo
    sede_id="demo-001",           # default para el MVP
    uploaded_by=str(chat_id),     # ID de Telegram como uploader
    mime_type="image/jpeg",       # o "image/png", "application/pdf"
)
# result.document_id contiene el ID generado por el pipeline
```

> **Importante:** El pipeline genera el `document_id` internamente. El handler no lo inyecta.

## Caso alternativo: documento enviado como archivo (no como foto)

Telegram comprime las fotos enviadas normalmente. Si el usuario envía la imagen como "documento" (sin compresión), la calidad es mayor. Se debe soportar ambos casos, incluyendo PDF.

```
Usuario envía archivo como Documento Telegram
    ↓
handler on_document(update, context)
    ↓
check_access(update)
    ↓
Verificar mime_type:
    - image/jpeg, image/png, image/webp, image/tiff → procesar como imagen
    - application/pdf → procesar como PDF (mime_type="application/pdf")
    - cualquier otro → responder "Solo acepto imágenes o PDF de facturas."
    ↓
Continuar con mismo flujo desde download_telegram_file()
```

> **Nota sobre PDF:** El pipeline ya soporta `application/pdf` — extrae texto con pdfplumber y usa OCR de ser necesario. Usar `mime_type="application/pdf"` al llamar `pipeline.process()`.

## Criterios de aceptación

### Handler de foto
- [ ] `src/telegram_bot/handlers.py` — función `on_photo(update, context)`
  - Registrada en bot.py con `application.add_handler(MessageHandler(filters.PHOTO, on_photo))`
- [ ] Responde al usuario en < 500ms con mensaje de "procesando" antes de iniciar el pipeline
- [ ] Usa `await update.message.reply_text(...)` para el feedback inmediato
- [ ] Selecciona la foto de mayor resolución: último elemento de `update.message.photo`
- [ ] Llama `check_access(update)` antes de procesar

### Handler de documento (imagen/PDF sin comprimir)
- [ ] Función `on_document(update, context)` registrada con `filters.Document.ALL`
- [ ] Verifica `update.message.document.mime_type` antes de procesar
- [ ] Tipos aceptados: `image/jpeg`, `image/png`, `image/webp`, `image/tiff`, `application/pdf`
- [ ] Responde "Solo acepto imágenes (JPG, PNG, WEBP) o PDF de facturas." si es otro tipo
- [ ] Llama `check_access(update)` antes de procesar

### Descargador
- [ ] `src/telegram_bot/downloader.py` — función `download_telegram_file(file_id: str, bot: Bot) -> bytes`
  - Llama `await bot.get_file(file_id)` para obtener la URL
  - Descarga con `await telegram_file.download_as_bytearray()`
  - Retorna `bytes`
- [ ] Si la descarga falla (timeout, error de red): lanza `TelegramDownloadError` con mensaje descriptivo
- [ ] Tamaño máximo: `TELEGRAM_MAX_FILE_SIZE_MB` (default 20MB). Si se supera: notificar al usuario y no procesar

### Integración con el pipeline y store
- [ ] Pipeline se llama con `image_bytes=bytes` — no con file_obj ni SpooledTemporaryFile
- [ ] Pipeline se ejecuta en `asyncio.get_event_loop().run_in_executor(None, ...)` para no bloquear el event loop
- [ ] Después de `pipeline.process()`: llamar `store.save(result)` para que el documento sea accesible por los comandos de Spec-24
- [ ] `context.user_data["last_document_id"] = result.document_id`
- [ ] Si el pipeline lanza excepción: capturar, loguear con traceback, responder al usuario con mensaje genérico

### Mensajes al usuario
| Situación | Mensaje |
|---|---|
| Foto/doc recibido | "Recibido. Procesando tu factura, aguarda un momento..." |
| Pipeline completado | (delegar a Spec-23) |
| Archivo demasiado grande | "El archivo supera el límite permitido ({MAX}MB). Por favor enviá una imagen más pequeña." |
| Tipo de archivo no soportado | "Solo acepto imágenes (JPG, PNG, WEBP) o PDF de facturas." |
| Error de procesamiento | "Ocurrió un error al procesar la factura. Por favor intentá de nuevo." |
| Sin permiso | "No tenés permiso para usar este bot." |

## Variables de entorno

| Variable | Tipo | Default | Descripcion |
|---|---|---|---|
| `TELEGRAM_MAX_FILE_SIZE_MB` | int | `20` | Tamaño máximo de imagen en MB |

## Notas de implementacion
- No crear `Pipeline()` nuevo en cada mensaje — reusar la instancia `_pipeline` de `api/main.py` inyectada al inicializar el bot, o importar desde un módulo compartido.
- El semáforo de concurrencia (`asyncio.Semaphore`) es opcional para el MVP pero recomendado si hay agentes LLM reales: limita a N ejecuciones paralelas del pipeline.
- Si la confianza del resultado es baja y el usuario envió foto (comprimida por Telegram), incluir en la respuesta (Spec-23) la sugerencia de reenviar como documento para mayor calidad.
