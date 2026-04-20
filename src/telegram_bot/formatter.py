"""Formateadores de mensajes Telegram — Spec-23."""
from __future__ import annotations

from typing import Optional


def _fmt_amount(value) -> str:
    if value is None:
        return "no detectado"
    try:
        v = float(value)
        # es-AR: punto para miles, coma para decimales
        formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_field(result, field_name: str, is_amount: bool = False) -> str:
    f = result.extracted_fields.get(field_name)
    if not f or f.value is None:
        return "no detectado"
    return _fmt_amount(f.value) if is_amount else str(f.value)


def _truncate(text: str, limit: int = 4096) -> str:
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def format_result_message(result) -> str:
    confianza_pct = f"{result.confidence_score * 100:.0f}%"
    routing_label = result.routing.value if result.routing else "—"

    lines = [
        "<b>Factura procesada correctamente</b>\n",
        f"<b>Proveedor:</b>  {result.provider or 'no detectado'}",
        f"<b>Número:</b>     {_fmt_field(result, 'reference_number')}",
        f"<b>Fecha:</b>      {_fmt_field(result, 'issue_date')}",
        f"<b>Subtotal:</b>   {_fmt_field(result, 'subtotal', is_amount=True)}",
        f"<b>IVA:</b>        {_fmt_field(result, 'tax_amount', is_amount=True)}",
        f"<b>Total:</b>      {_fmt_field(result, 'total_amount', is_amount=True)}",
        "",
        f"<b>Confianza:</b> {confianza_pct} ({routing_label})",
        "",
        "Usá /aprobar para enviar a SAP o /rechazar para descartar.",
        f"<code>ID: {result.document_id}</code>",
    ]
    return _truncate("\n".join(lines))


def format_low_confidence_message(result) -> str:
    confianza_pct = f"{result.confidence_score * 100:.0f}%"

    low_fields = [
        (name, field)
        for name, field in result.extracted_fields.items()
        if field.confidence < 0.70
    ]

    lines = [
        f"<b>Factura procesada con confianza baja ({confianza_pct})</b>\n",
        "Campos con dudas:",
    ]

    if low_fields:
        for name, field in low_fields:
            val = str(field.value) if field.value is not None else "no detectado"
            pct = f"{field.confidence * 100:.0f}%"
            lines.append(f"  • <b>{name}:</b> {val} ({pct})")
    else:
        lines.append("  (sin campos específicos identificados)")

    lines += [
        "",
        "<i>Recomendación: reenvía la imagen como archivo adjunto (sin comprimir) para mayor calidad.</i>",
        "",
        f"<code>ID: {result.document_id}</code>",
    ]
    return _truncate("\n".join(lines))


def format_error_message() -> str:
    return "Ocurrió un error al procesar la factura. Por favor intentá de nuevo."
