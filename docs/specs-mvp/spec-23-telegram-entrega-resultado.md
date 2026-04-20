# Triunfo — Spec-23 Telegram Entrega de Resultado (PDF + Resumen) v1.1
# Version: 1.1
# Fecha: 2026-04-20
# Estado: Pendiente

## Objetivo
Una vez que el pipeline termina de procesar la imagen, formatear el resultado y enviarlo al usuario vía Telegram. Si el routing es AUTO_APPROVE o HITL_STANDARD, adjuntar el PDF generado. Si el routing es HITL_PRIORITY o AUTO_REJECT, notificar con detalle para que el usuario tome acción.

## Ubicación
```
src/telegram_bot/handlers.py  — on_result(), funciones de formato
src/telegram_bot/formatter.py — format_result_message(), format_low_confidence_message()
```

Depende de: Spec-22 (resultado de pipeline disponible), Spec-03 (estructura DocumentResult), `src/pdf_generator.py` (generate_result_pdf).

## Flujo

```
DocumentResult retornado por pipeline (desde Spec-22)
    ↓
formatter.format_result_message(result) → texto HTML para Telegram
    ↓
Branchar sobre result.routing (enum RoutingDecision):
    ├── AUTO_APPROVE o HITL_STANDARD
    │     → generar PDF: from src.pdf_generator import generate_result_pdf; pdf_bytes = generate_result_pdf(result)
    │     → enviar bot.send_document(chat_id, document=InputFile(pdf_bytes, "factura.pdf"), caption=mensaje, parse_mode="HTML")
    │     → si caption > 1024 chars: enviar doc sin caption, luego mensaje de texto separado
    │     → incluir teclado inline: [Aprobar ✓] [Rechazar ✗]
    ├── HITL_PRIORITY
    │     → enviar solo mensaje de texto con format_low_confidence_message(result)
    │     → sugerir reenviar como archivo sin comprimir
    └── AUTO_REJECT
          → enviar mensaje indicando que no se pudo procesar, pedir reenvío con mejor imagen
```

## Acceso a campos del modelo (importante)

```python
# DocumentResult — src/models/document.py
result.routing          # RoutingDecision enum: AUTO_APPROVE | HITL_STANDARD | HITL_PRIORITY | AUTO_REJECT
result.confidence_score # float 0.0-1.0
result.provider         # str | None
result.extracted_fields # Dict[str, ConciliationField]

# Acceder a un campo extraído:
field = result.extracted_fields.get("total_amount")
value = field.value if field else None
confidence = field.confidence if field else 0.0

# Comparar routing:
from src.models.document import RoutingDecision
if result.routing in (RoutingDecision.AUTO_APPROVE, RoutingDecision.HITL_STANDARD):
    ...
```

> **Incorrecto:** `result.routing.decision` o `result.confidence` — esos atributos no existen.

## Formato del mensaje de resultado (routing alto)

```html
<b>Factura procesada correctamente</b>

<b>Proveedor:</b>  Edenor
<b>Número:</b>     000-12345678
<b>Fecha:</b>      15/04/2026
<b>Total:</b>      $45.230,00
<b>IVA:</b>        $7.520,00
<b>Subtotal:</b>   $37.710,00

<b>Confianza:</b> 91% (AUTO_APPROVE)

Usá /aprobar para enviar a SAP o /rechazar para descartar.
<code>ID: abc-123-def</code>
```

## Formato del mensaje de baja confianza (HITL_PRIORITY)

```html
<b>Factura procesada con confianza baja (62%)</b>

Campos con dudas:
  • <b>total_amount:</b> $45.230,00 (58%)
  • <b>invoice_number:</b> no detectado
  • <b>issue_date:</b> 15/04/2026 (72%)

<i>Recomendación: reenvía la imagen como archivo adjunto (sin comprimir) para mayor calidad.</i>

<code>ID: abc-123-def</code>
```

## Tabla de routing → acción del bot

| `result.routing` | Acción |
|---|---|
| `AUTO_APPROVE` | Enviar PDF + mensaje + botones inline |
| `HITL_STANDARD` | Enviar PDF + mensaje + botones inline |
| `HITL_PRIORITY` | Enviar solo mensaje con advertencia, sin PDF |
| `AUTO_REJECT` | Enviar mensaje de rechazo, sugerir reenvío |

> **Nota:** El bot no recalcula routing desde confidence_score — usa directamente `result.routing` que el pipeline ya determinó.

## Criterios de aceptación

### Formatter
- [ ] `src/telegram_bot/formatter.py` — función `format_result_message(result: DocumentResult) -> str`
  - Retorna texto en HTML (`parse_mode="HTML"`)
  - Incluye: proveedor, número de factura, fecha, subtotal, IVA, total, confianza global (como %), routing decision
  - Si un campo no fue extraído: mostrar "no detectado"
  - Montos formateados con separador de miles `.` y decimales `,` (estilo es-AR): `$45.230,00`
- [ ] Función `format_low_confidence_message(result: DocumentResult) -> str`
  - Lista campos con `field.confidence < 0.70` con su valor y porcentaje
  - Incluye sugerencia de reenvío como archivo
- [ ] Función `format_error_message() -> str`
  - Mensaje genérico sin exponer detalles internos

### Handler de resultado
- [ ] `on_result(chat_id: int, result: DocumentResult, bot: Bot)` en `handlers.py`
  - Llamado desde `on_photo` / `on_document` al terminar el pipeline
- [ ] Si `result.routing in (AUTO_APPROVE, HITL_STANDARD)`:
  - Importar `from src.pdf_generator import generate_result_pdf` y llamar directamente (no HTTP)
  - Enviar con `await bot.send_document(chat_id, document=InputFile(pdf_bytes, filename="factura.pdf"), caption=mensaje, parse_mode="HTML", reply_markup=teclado_inline)`
  - Si caption > 1024 chars: enviar documento sin caption + mensaje de texto separado
- [ ] Si `result.routing == HITL_PRIORITY`:
  - Enviar `format_low_confidence_message(result)` con `parse_mode="HTML"`
- [ ] Si `result.routing == AUTO_REJECT`:
  - Enviar mensaje indicando que no se pudo procesar y sugerir reenviar con mejor imagen
- [ ] Si la generación de PDF falla: enviar igualmente el mensaje de texto, loguear el error

### Botones inline (solo cuando se envía PDF)
- [ ] Teclado inline con dos botones:
  - `[Aprobar ✓]` — callback_data: `aprobar:{document_id}`
  - `[Rechazar ✗]` — callback_data: `rechazar:{document_id}`
- [ ] El handler de callback se define en Spec-24

## Variables de entorno
Ninguna adicional. El umbral de routing está determinado por el pipeline, no por el bot.

## Notas de implementacion
- Usar `parse_mode="HTML"` en todos los mensajes (no MarkdownV2) — evita problemas con caracteres especiales en datos de facturas (puntos, paréntesis, guiones en montos y fechas).
- Para formatear montos es-AR: `f"${amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")` o usar `locale`.
- Telegram limita caption a 1024 chars y mensaje a 4096 chars. Si el resumen supera 4096: truncar y agregar `...`.
- El PDF se genera en memoria como `bytes` — no escribir a disco.
- El nombre del PDF puede incluir el número de factura si está disponible: `f"factura_{invoice_number or result.document_id[:8]}.pdf"`.
