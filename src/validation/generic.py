"""Validaciones genéricas para todos los proveedores — Spec-05."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Dict, List, Optional, Set

from src.models.document import ConciliationField, ValidationResult

# Registro en memoria de documentos procesados (clave: ref + provider + date)
_DUPLICATE_REGISTRY: Set[str] = set()

MAX_AMOUNT = 999_999.0
MIN_AMOUNT = 0.01
MAX_DATE_DIFF_DAYS = 180
MIN_ISSUE_DATE = date(2020, 1, 1)
REF_MIN_LEN = 5
REF_MAX_LEN = 30
ARITH_TOLERANCE = 0.01


def validate_generic(
    fields: Dict[str, ConciliationField],
    provider_name: str = "",
) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    _check_amounts(fields, errors, warnings)
    _check_dates(fields, errors, warnings)
    _check_reference(fields, errors, warnings)
    _check_duplicates(fields, provider_name, errors)
    _check_arithmetic(fields, errors)

    return ValidationResult(
        is_consistent=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Validaciones internas
# ---------------------------------------------------------------------------

def _get_val(fields: Dict[str, ConciliationField], key: str):
    cf = fields.get(key)
    return cf.value if cf else None


def _check_amounts(
    fields: Dict[str, ConciliationField],
    errors: List[str],
    warnings: List[str],
) -> None:
    total = _get_val(fields, "total_amount")
    if total is None:
        errors.append("Campo crítico total_amount faltante")
        return

    try:
        total_f = float(total)
    except (TypeError, ValueError):
        errors.append(f"total_amount no es numérico: {total!r}")
        return

    if total_f <= 0:
        errors.append(f"total_amount debe ser > 0 (valor: {total_f})")
    elif total_f < MIN_AMOUNT:
        warnings.append(f"total_amount muy bajo: {total_f}")
    elif total_f > MAX_AMOUNT:
        errors.append(f"total_amount excede límite {MAX_AMOUNT}: {total_f}")


def _check_dates(
    fields: Dict[str, ConciliationField],
    errors: List[str],
    warnings: List[str],
) -> None:
    issue_raw = _get_val(fields, "issue_date")
    due_raw = _get_val(fields, "due_date")

    issue_date: Optional[date] = None
    if issue_raw:
        try:
            issue_date = date.fromisoformat(str(issue_raw)[:10])
        except ValueError:
            errors.append(f"issue_date formato inválido: {issue_raw!r}")

    if issue_date:
        today = date.today()
        if issue_date > today:
            errors.append(f"issue_date en el futuro: {issue_date}")
        if issue_date < MIN_ISSUE_DATE:
            errors.append(f"issue_date muy antigua: {issue_date}")

    if due_raw:
        try:
            due_date = date.fromisoformat(str(due_raw)[:10])
        except ValueError:
            errors.append(f"due_date formato inválido: {due_raw!r}")
            return

        if issue_date and due_date < issue_date:
            errors.append(f"due_date ({due_date}) anterior a issue_date ({issue_date})")
        if issue_date and (due_date - issue_date).days > MAX_DATE_DIFF_DAYS:
            warnings.append(
                f"due_date {MAX_DATE_DIFF_DAYS} días después de issue_date"
            )
    else:
        warnings.append("Falta campo recomendado: due_date")

    # Validar período si está presente
    period_start_raw = _get_val(fields, "period_start")
    period_end_raw = _get_val(fields, "period_end")
    if period_start_raw and period_end_raw:
        try:
            ps = date.fromisoformat(str(period_start_raw)[:10])
            pe = date.fromisoformat(str(period_end_raw)[:10])
            if pe <= ps:
                errors.append(f"period_end ({pe}) debe ser > period_start ({ps})")
            if (pe - ps).days > 35:
                warnings.append(f"Período inusualmente largo: {(pe - ps).days} días")
        except ValueError:
            pass


def _check_reference(
    fields: Dict[str, ConciliationField],
    errors: List[str],
    warnings: List[str],
) -> None:
    ref = _get_val(fields, "reference_number")
    if not ref:
        warnings.append("Falta campo recomendado: reference_number")
        return

    ref_str = str(ref).strip()
    if len(ref_str) < REF_MIN_LEN:
        errors.append(f"reference_number muy corto ({len(ref_str)} chars): {ref_str!r}")
    elif len(ref_str) > REF_MAX_LEN:
        errors.append(f"reference_number muy largo ({len(ref_str)} chars): {ref_str!r}")

    if re.search(r"[<>\"\'\`\\]", ref_str):
        errors.append(f"reference_number contiene caracteres inválidos: {ref_str!r}")


def _check_duplicates(
    fields: Dict[str, ConciliationField],
    provider_name: str,
    errors: List[str],
) -> None:
    ref = _get_val(fields, "reference_number")
    issue = _get_val(fields, "issue_date")
    if not ref or not issue:
        return

    key = f"{str(ref).strip().lower()}|{provider_name.lower()}|{str(issue)[:10]}"
    if key in _DUPLICATE_REGISTRY:
        errors.append(
            f"Documento duplicado detectado: ref={ref}, provider={provider_name}, date={issue}"
        )
    else:
        _DUPLICATE_REGISTRY.add(key)


def _check_arithmetic(
    fields: Dict[str, ConciliationField],
    errors: List[str],
) -> None:
    total = _get_val(fields, "total_amount")
    subtotal = _get_val(fields, "subtotal")
    tax = _get_val(fields, "tax_amount")

    if total is None or subtotal is None or tax is None:
        return

    try:
        total_f = float(total)
        subtotal_f = float(subtotal)
        tax_f = float(tax)
    except (TypeError, ValueError):
        return

    expected = subtotal_f + tax_f
    if abs(expected - total_f) > ARITH_TOLERANCE:
        errors.append(
            f"Inconsistencia aritmética: subtotal({subtotal_f}) + tax({tax_f}) "
            f"= {expected:.2f} ≠ total({total_f})"
        )


def clear_duplicate_registry() -> None:
    """Para tests y demos — limpia el registro en memoria."""
    _DUPLICATE_REGISTRY.clear()
