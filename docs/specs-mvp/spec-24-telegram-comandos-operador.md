# Triunfo — Spec-24 Telegram Comandos de Operador v1.1
# Version: 1.1
# Fecha: 2026-04-20
# Estado: Pendiente

## Objetivo
Exponer comandos de Telegram que permitan al operador consultar el estado de documentos procesados y aprobar o rechazar el envío a SAP, todo desde el chat de Telegram. Este spec cubre `/ayuda`, `/help`, `/estado`, `/aprobar`, `/rechazar` y los callbacks de los botones inline del Spec-23.

## Ubicación
```
src/telegram_bot/handlers.py — funciones de comando y callback handlers
```

Depende de: Spec-21 (bot), Spec-23 (botones inline generados allí), `src/store.py` (store compartido).

## Store compartido

Los documentos son guardados en `src/store.py` por el handler de foto (Spec-22). Los comandos acceden al mismo módulo:

```python
from src import store

# Obtener documento
doc = store.get(document_id)          # → DocumentResult | None

# Aprobar (incluye lógica SAP, lanza KeyError/ValueError en estado inválido)
sap_resp = store.approve(document_id)

# Rechazar
store.reject(document_id)             # lanza KeyError si no existe

# Verificar estado
store.is_approved(document_id)        # → bool (sap_response is not None)
store.is_rejected(document_id)        # → bool
```

> No hacer llamadas HTTP internas entre módulos del mismo proceso.

## Comandos disponibles

| Comando | Sintaxis | Descripcion |
|---|---|---|
| `/start` | `/start` | Mensaje de bienvenida (definido en Spec-21) |
| `/ayuda` | `/ayuda` | Lista todos los comandos con descripción |
| `/help` | `/help` | Alias de /ayuda (estándar Telegram) |
| `/estado` | `/estado [doc_id]` | Muestra el estado actual del documento |
| `/aprobar` | `/aprobar [doc_id]` | Aprueba el documento y lo envía al mock SAP |
| `/rechazar` | `/rechazar [doc_id]` | Rechaza y descarta el documento |

Si no se pasa `doc_id` en `/estado`, `/aprobar` o `/rechazar`, usar el último documento procesado en esa sesión (`context.user_data.get("last_document_id")`).

## Flujo de /aprobar

```
Usuario envía /aprobar [doc_id]
    ↓
check_access(update) — si falla: responder y retornar
    ↓
Resolver doc_id (context.args[0] si existe, sino context.user_data.get("last_document_id"))
    ↓
Si no hay doc_id: "No tenés ningún documento procesado en esta sesión. Enviame una foto primero."
    ↓
try:
    sap_resp = store.approve(doc_id)
    → "Documento {doc_id[:8]} aprobado y enviado a SAP correctamente."
except KeyError:
    → "No encontré el documento {doc_id}. Verificá el ID."
except ValueError as e:
    → str(e)   # "ya fue aprobado", "rechazado automáticamente", "rechazado por operador"
```

## Flujo de callback (botones inline)

```
Usuario presiona botón [Aprobar ✓] o [Rechazar ✗] del mensaje Spec-23
    ↓
CallbackQueryHandler recibe callback_data: "aprobar:{doc_id}" o "rechazar:{doc_id}"
    ↓
await query.answer()  ← obligatorio para quitar el spinner del botón
    ↓
check_access(update)
    ↓
Ejecutar mismo flujo que /aprobar o /rechazar
    ↓
await query.edit_message_reply_markup(reply_markup=None)  ← deshabilitar botones
    ↓
Responder con mensaje de confirmación
```

## Formato de /estado

```html
<b>Estado del documento</b> <code>abc-123-def</code>

<b>Proveedor:</b>  Edenor
<b>Número:</b>     000-12345678
<b>Routing:</b>    HITL_STANDARD
<b>Confianza:</b>  78%
<b>Procesado:</b>  20/04/2026 14:32
<b>Aprobado:</b>   No
<b>Rechazado:</b>  No

Usá /aprobar abc-123-def para enviarlo a SAP.
```

"Aprobado: Sí" cuando `store.is_approved(doc_id)` es True.
"Rechazado: Sí" cuando `store.is_rejected(doc_id)` es True.

## Criterios de aceptación

### Control de acceso (función utilitaria)
- [ ] Función `check_access(update: Update) -> bool` en `handlers.py`
  - Lee `TELEGRAM_ALLOWED_USERS` del entorno (lista de IDs separados por coma)
  - Si la lista está vacía: retornar True (sin restricción)
  - Si `str(update.effective_user.id)` está en la lista: retornar True
  - Si no: `await update.message.reply_text("No tenés permiso para usar este bot.")` y retornar False
  - Se llama al inicio de TODOS los handlers (foto, documento, comandos, callbacks)

### /ayuda y /help
- [ ] Función `cmd_ayuda(update, context)` registrada con `CommandHandler("ayuda", cmd_ayuda)` y `CommandHandler("help", cmd_ayuda)`
- [ ] Lista todos los comandos con descripción en mensaje HTML

### /estado
- [ ] Función `cmd_estado(update, context)` registrada con `CommandHandler("estado", cmd_estado)`
- [ ] Parsea `context.args[0]` si existe, sino `context.user_data.get("last_document_id")`
- [ ] Si no hay doc_id: "No tenés ningún documento procesado en esta sesión. Enviame una foto primero."
- [ ] Muestra: proveedor, número de factura, routing, confianza (%), timestamp de procesamiento, estado aprobado/rechazado
- [ ] Llama `check_access(update)` primero

### /aprobar
- [ ] Función `cmd_aprobar(update, context)` registrada con `CommandHandler("aprobar", cmd_aprobar)`
- [ ] Resuelve doc_id igual que /estado
- [ ] Llama `store.approve(doc_id)` — maneja `KeyError` y `ValueError`
- [ ] Respuesta de éxito incluye el doc_id[:8] para trazabilidad
- [ ] Llama `check_access(update)` primero

### /rechazar
- [ ] Función `cmd_rechazar(update, context)` registrada con `CommandHandler("rechazar", cmd_rechazar)`
- [ ] Resuelve doc_id igual que /estado
- [ ] Llama `store.reject(doc_id)` — maneja `KeyError`
- [ ] Respuesta: "Documento {doc_id[:8]} rechazado y descartado."
- [ ] Llama `check_access(update)` primero

### Callback de botones inline
- [ ] `CallbackQueryHandler(handle_inline_callback, pattern="^(aprobar|rechazar):")` registrado en bot.py
- [ ] Función `handle_inline_callback(update, context)` parsea el pattern y delega a la lógica de cmd_aprobar / cmd_rechazar
- [ ] Siempre llama `await query.answer()` al inicio del handler para evitar timeout de Telegram
- [ ] Edita el mensaje original para remover los botones inline después de la acción (evitar doble click)
- [ ] Llama `check_access(update)` después de `query.answer()`

## Notas de implementacion
- `context.user_data` persiste solo en memoria. Si el servidor se reinicia, el usuario debe especificar el doc_id explícitamente. Aceptable para el MVP.
- `store.approve()` lanza `ValueError` con mensajes legibles directamente enviables al usuario.
- El separador `:` en `callback_data` es seguro — los UUID solo contienen `-` y caracteres alfanuméricos.
- Registrar los handlers de comandos en `bot.py` antes del handler genérico de mensajes.
