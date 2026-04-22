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


_IVA_KEYWORDS = ("i.v.a", "iva")


def _is_iva_item(desc: str) -> bool:
    lower = desc.lower()
    return any(lower.startswith(kw) for kw in _IVA_KEYWORDS)


def _fmt_taxes(result) -> str:
    f = result.extracted_fields.get("impuestos_tasas")
    if not f or not f.value:
        return ""
    items = f.value
    if not isinstance(items, list) or not items:
        return ""
    # Si hay IVA calculado como campo propio, omitirlo del bloque para no duplicar
    has_tax_field = (
        result.extracted_fields.get("tax_amount") is not None
        and result.extracted_fields["tax_amount"].value is not None
    )
    lines = ["", "<b>Impuestos y tasas:</b>"]
    for item in items:
        if isinstance(item, dict):
            desc = item.get("descripcion") or "—"
            if has_tax_field and _is_iva_item(desc):
                continue
            monto = item.get("monto")
            lines.append(f"  • {desc}: {_fmt_amount(monto)}")
    if len(lines) == 2:
        return ""
    return "\n".join(lines)


def format_result_message(result) -> str:
    confianza_pct = f"{result.confidence_score * 100:.0f}%"
    routing = result.routing.value if result.routing else "—"

    is_low_confidence = result.routing and result.routing.value == "HITL_PRIORITY"
    header = (
        "<b>⚠️ Factura procesada con confianza baja</b>\n"
        if is_low_confidence
        else "<b>Factura procesada correctamente</b>\n"
    )

    customer_address = _fmt_field(result, "customer_address")

    lines = [
        header,
        f"<b>Proveedor:</b>   {_fmt_field(result, 'provider_name')}",
        f"<b>A nombre de:</b> {_fmt_field(result, 'customer_name')}",
    ]
    if customer_address != "no detectado":
        lines.append(f"<b>Dirección:</b>   {customer_address}")
    lines += [
        f"<b>NIC:</b>         {_fmt_field(result, 'nic')}",
        f"<b>Número:</b>      {_fmt_field(result, 'reference_number')}",
        f"<b>Fecha:</b>       {_fmt_field(result, 'issue_date')}",
        f"<b>Subtotal:</b>    {_fmt_field(result, 'net_amount', is_amount=True)}",
        f"<b>IVA:</b>         {_fmt_field(result, 'tax_amount', is_amount=True)}",
        f"<b>Total:</b>       {_fmt_field(result, 'total_amount', is_amount=True)}",
    ]

    taxes_block = _fmt_taxes(result)
    if taxes_block:
        lines.append(taxes_block)

    lines += [
        "",
        f"<b>Confianza:</b> {confianza_pct} ({routing})",
    ]

    if is_low_confidence:
        low_fields = [
            (name, field)
            for name, field in result.extracted_fields.items()
            if field.confidence < 0.70 and field.value is not None
            and name != "impuestos_tasas"
        ]
        if low_fields:
            lines.append("\n<i>Campos con baja confianza — revisá antes de aprobar:</i>")
            for name, field in low_fields:
                pct = f"{field.confidence * 100:.0f}%"
                lines.append(f"  • <b>{name}:</b> {field.value} ({pct})")

    lines += [
        "",
        "Usá los botones para aprobar o rechazar.",
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
