"""Handlers del bot de Telegram — Specs 22, 23 y 24."""
from __future__ import annotations

import asyncio
import functools
import io
import os
import time
import traceback
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import ContextTypes

from src import store
from src.logging_setup import setup_logging
from src.telegram_bot.downloader import (
    SUPPORTED_MIME_TYPES,
    TelegramDownloadError,
    download_telegram_file,
)
from src.telegram_bot.formatter import (
    format_error_message,
    format_low_confidence_message,
    format_result_message,
)

logger = setup_logging("triunfo.telegram.handlers")

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from src.pipeline.processor import Pipeline
        _pipeline = Pipeline()
    return _pipeline


# ---------------------------------------------------------------------------
# Control de acceso — Spec-24
# ---------------------------------------------------------------------------

async def check_access(update: Update) -> bool:
    allowed_raw = os.getenv("TELEGRAM_ALLOWED_USERS", "").strip()
    if not allowed_raw:
        return True

    allowed_set = {uid.strip() for uid in allowed_raw.split(",") if uid.strip()}
    user_id = str(update.effective_user.id) if update.effective_user else ""

    if user_id in allowed_set:
        return True

    msg = "No tenés permiso para usar este bot."
    if update.callback_query:
        await update.callback_query.answer(msg, show_alert=True)
    elif update.message:
        await update.message.reply_text(msg)
    return False


# ---------------------------------------------------------------------------
# Handlers de foto y documento — Spec-22
# ---------------------------------------------------------------------------

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return

    chat_id = update.effective_chat.id
    max_mb = int(os.getenv("TELEGRAM_MAX_FILE_SIZE_MB", "20"))
    max_bytes = max_mb * 1024 * 1024

    # Foto de mayor resolución = último elemento de la lista
    photo = update.message.photo[-1]

    if photo.file_size and photo.file_size > max_bytes:
        await update.message.reply_text(
            f"El archivo supera el límite permitido ({max_mb}MB). "
            "Por favor enviá una imagen más pequeña."
        )
        return

    await update.message.reply_text("Recibido. Procesando tu factura, aguarda un momento...")

    try:
        image_bytes = await download_telegram_file(photo.file_id, context.bot)
    except TelegramDownloadError as e:
        logger.error(f"Error descargando foto: {e}")
        await update.message.reply_text(format_error_message())
        return

    await _process_and_respond(
        update=update,
        context=context,
        chat_id=chat_id,
        image_bytes=image_bytes,
        file_name=f"factura_{chat_id}_{int(time.time())}.jpg",
        mime_type="image/jpeg",
    )


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return

    chat_id = update.effective_chat.id
    doc = update.message.document
    mime_type = (doc.mime_type or "").lower()

    if mime_type not in SUPPORTED_MIME_TYPES:
        await update.message.reply_text("Solo acepto imágenes (JPG, PNG, WEBP) o PDF de facturas.")
        return

    max_mb = int(os.getenv("TELEGRAM_MAX_FILE_SIZE_MB", "20"))
    max_bytes = max_mb * 1024 * 1024
    if doc.file_size and doc.file_size > max_bytes:
        await update.message.reply_text(
            f"El archivo supera el límite permitido ({max_mb}MB). "
            "Por favor enviá un archivo más pequeño."
        )
        return

    await update.message.reply_text("Recibido. Procesando tu factura, aguarda un momento...")

    try:
        image_bytes = await download_telegram_file(doc.file_id, context.bot)
    except TelegramDownloadError as e:
        logger.error(f"Error descargando documento: {e}")
        await update.message.reply_text(format_error_message())
        return

    ext = "pdf" if mime_type == "application/pdf" else "jpg"
    await _process_and_respond(
        update=update,
        context=context,
        chat_id=chat_id,
        image_bytes=image_bytes,
        file_name=f"factura_{chat_id}_{int(time.time())}.{ext}",
        mime_type=mime_type,
    )


async def _process_and_respond(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    image_bytes: bytes,
    file_name: str,
    mime_type: str,
) -> None:
    try:
        pipeline = _get_pipeline()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            functools.partial(
                pipeline.process,
                image_bytes=image_bytes,
                file_name=file_name,
                uploaded_by=str(chat_id),
                mime_type=mime_type,
            ),
        )
        store.save(result)
        context.user_data["last_document_id"] = result.document_id
        await on_result(chat_id, result, context.bot)
    except Exception:
        logger.error(f"Error en pipeline:\n{traceback.format_exc()}")
        await update.message.reply_text(format_error_message())


# ---------------------------------------------------------------------------
# Entrega del resultado — Spec-23
# ---------------------------------------------------------------------------

async def on_result(chat_id: int, result, bot) -> None:
    from src.models.document import RoutingDecision

    routing = result.routing
    msg = format_result_message(result)

    actionable_routings = (
        RoutingDecision.AUTO_APPROVE,
        RoutingDecision.HITL_STANDARD,
        RoutingDecision.HITL_PRIORITY,
    )

    if routing in actionable_routings:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Aprobar ✓", callback_data=f"aprobar:{result.document_id}"),
                InlineKeyboardButton("Rechazar ✗", callback_data=f"rechazar:{result.document_id}"),
            ]
        ])
        pdf_bytes = _generate_pdf(result)
        if pdf_bytes:
            invoice_num = _get_field_value(result, "reference_number")
            filename = f"factura_{invoice_num or result.document_id[:8]}.pdf"
            caption = msg if len(msg) <= 1024 else None
            try:
                await bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(io.BytesIO(pdf_bytes), filename=filename),
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                if caption is None:
                    await bot.send_message(
                        chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=keyboard
                    )
                return
            except Exception:
                logger.error(f"Error enviando PDF:\n{traceback.format_exc()}")
        # fallback sin PDF
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=keyboard)

    else:
        # AUTO_REJECT
        reject_msg = (
            "<b>No fue posible procesar la factura.</b>\n\n"
            "La imagen no tiene suficiente calidad para extraer los datos.\n"
            "Por favor intentá reenviar con mejor iluminación o como archivo adjunto sin comprimir."
        )
        await bot.send_message(chat_id=chat_id, text=reject_msg, parse_mode="HTML")


def _generate_pdf(result) -> Optional[bytes]:
    try:
        from src.pdf_generator import generate_result_pdf
        return generate_result_pdf(result)
    except Exception:
        logger.error(f"Error generando PDF:\n{traceback.format_exc()}")
        return None


def _get_field_value(result, field_name: str):
    f = result.extracted_fields.get(field_name)
    return f.value if f else None


# ---------------------------------------------------------------------------
# Comandos de operador — Spec-24
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return
    await update.message.reply_text(
        "Bienvenido al sistema Triunfo de procesamiento de facturas.\n"
        "Enviame una foto de tu factura y te devuelvo los datos extraidos.\n"
        "Para mas informacion usa /ayuda."
    )


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return
    texto = (
        "<b>Comandos disponibles</b>\n\n"
        "/start — Mensaje de bienvenida\n"
        "/ayuda — Esta ayuda\n"
        "/estado [doc_id] — Estado de un documento procesado\n"
        "/aprobar [doc_id] — Aprobar y enviar a SAP\n"
        "/rechazar [doc_id] — Rechazar y descartar\n\n"
        "También podés enviar una foto o PDF de factura directamente."
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return

    doc_id = _resolve_doc_id(context)
    if not doc_id:
        await update.message.reply_text(
            "No tenés ningún documento procesado en esta sesión. Enviame una foto primero."
        )
        return

    doc = store.get(doc_id)
    if not doc:
        await update.message.reply_text(f"No encontré el documento <code>{doc_id}</code>.", parse_mode="HTML")
        return

    aprobado = "Sí" if store.is_approved(doc_id) else "No"
    rechazado = "Sí" if store.is_rejected(doc_id) else "No"
    confianza = f"{doc.confidence_score * 100:.0f}%"
    invoice_num = _get_field_value(doc, "reference_number") or "no detectado"
    procesado_at = doc.ingestion.uploaded_at[:19].replace("T", " ") if doc.ingestion else "—"

    texto = (
        f"<b>Estado del documento</b> <code>{doc_id[:8]}</code>\n\n"
        f"<b>Proveedor:</b>  {doc.provider or 'no detectado'}\n"
        f"<b>Número:</b>     {invoice_num}\n"
        f"<b>Routing:</b>    {doc.routing.value if doc.routing else '—'}\n"
        f"<b>Confianza:</b>  {confianza}\n"
        f"<b>Procesado:</b>  {procesado_at}\n"
        f"<b>Aprobado:</b>   {aprobado}\n"
        f"<b>Rechazado:</b>  {rechazado}\n"
    )
    if not store.is_approved(doc_id) and not store.is_rejected(doc_id):
        texto += f"\nUsá /aprobar {doc_id[:8]} para enviarlo a SAP."

    await update.message.reply_text(texto, parse_mode="HTML")


async def cmd_aprobar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return

    doc_id = _resolve_doc_id(context)
    if not doc_id:
        await update.message.reply_text(
            "No tenés ningún documento procesado en esta sesión. Enviame una foto primero."
        )
        return

    try:
        store.approve(doc_id)
        await update.message.reply_text(
            f"Documento <code>{doc_id[:8]}</code> aprobado y enviado a SAP correctamente.",
            parse_mode="HTML",
        )
    except KeyError:
        await update.message.reply_text(
            f"No encontré el documento <code>{doc_id}</code>. Verificá el ID.",
            parse_mode="HTML",
        )
    except ValueError as e:
        await update.message.reply_text(str(e))


async def cmd_rechazar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access(update):
        return

    doc_id = _resolve_doc_id(context)
    if not doc_id:
        await update.message.reply_text(
            "No tenés ningún documento procesado en esta sesión. Enviame una foto primero."
        )
        return

    try:
        store.reject(doc_id)
        await update.message.reply_text(
            f"Documento <code>{doc_id[:8]}</code> rechazado y descartado.",
            parse_mode="HTML",
        )
    except KeyError:
        await update.message.reply_text(
            f"No encontré el documento <code>{doc_id}</code>. Verificá el ID.",
            parse_mode="HTML",
        )


async def handle_inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not await check_access(update):
        return

    data = query.data or ""
    parts = data.split(":", 1)
    if len(parts) != 2:
        return

    action, doc_id = parts[0], parts[1]

    try:
        if action == "aprobar":
            store.approve(doc_id)
            msg = f"Documento <code>{doc_id[:8]}</code> aprobado y enviado a SAP correctamente."
        else:
            store.reject(doc_id)
            msg = f"Documento <code>{doc_id[:8]}</code> rechazado y descartado."
    except (KeyError, ValueError) as e:
        msg = str(e)

    # Deshabilitar botones del mensaje original
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    await query.message.reply_text(msg, parse_mode="HTML")


def _resolve_doc_id(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    if context.args:
        return context.args[0]
    return context.user_data.get("last_document_id")
