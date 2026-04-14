"""Validaciones específicas por proveedor — Spec-05."""
from __future__ import annotations

from typing import Dict, List, Optional

from src.models.document import ConciliationField, ValidationResult


def validate_provider(
    provider_id: str,
    fields: Dict[str, ConciliationField],
) -> ValidationResult:
    """Despacha al validador correcto según provider_id."""
    validators = {
        "edenor-001": _validate_edenor,
        "metrogas-001": _validate_metrogas,
        "factura-interna-001": _validate_factura_interna,
    }
    validator = validators.get(provider_id)
    if validator is None:
        return ValidationResult(is_consistent=True)
    return validator(fields)


def _get_val(fields: Dict[str, ConciliationField], key: str) -> Optional[object]:
    cf = fields.get(key)
    return cf.value if cf else None


# ---------------------------------------------------------------------------
# Edenor
# ---------------------------------------------------------------------------

def _validate_edenor(fields: Dict[str, ConciliationField]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    # meter_reading_end > meter_reading_start
    start_raw = _get_val(fields, "meter_reading_start")
    end_raw = _get_val(fields, "meter_reading_end")
    if start_raw is not None and end_raw is not None:
        try:
            start = float(str(start_raw).replace(",", "."))
            end = float(str(end_raw).replace(",", "."))
            if end <= start:
                errors.append(
                    f"Edenor: meter_reading_end ({end}) debe ser > start ({start})"
                )
        except ValueError:
            warnings.append("Edenor: lecturas de medidor no numéricas")

    # Consumo en rango [0, 10000] kWh
    consumption = _get_val(fields, "consumption")
    if consumption is not None:
        try:
            c = float(str(consumption).replace(",", "."))
            if c <= 0:
                errors.append(f"Edenor: consumo debe ser > 0 (valor: {c})")
            elif c > 10_000:
                errors.append(f"Edenor: consumo {c} kWh excede máximo 10000")
        except ValueError:
            warnings.append("Edenor: consumo no numérico")

    # tariff_code presente
    tariff = _get_val(fields, "tariff_code")
    if not tariff:
        warnings.append("Edenor: falta tariff_code")

    # Moneda ARS
    currency = _get_val(fields, "currency")
    if currency and str(currency).upper() != "ARS":
        errors.append(f"Edenor: moneda debe ser ARS, encontrado: {currency}")

    return ValidationResult(is_consistent=len(errors) == 0, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# Metrogas
# ---------------------------------------------------------------------------

def _validate_metrogas(fields: Dict[str, ConciliationField]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    # Consumo en rango [0, 5000] m³
    consumption = _get_val(fields, "consumption")
    if consumption is not None:
        try:
            c = float(str(consumption).replace(",", "."))
            if c <= 0:
                errors.append(f"Metrogas: consumo debe ser > 0 (valor: {c})")
            elif c > 5_000:
                errors.append(f"Metrogas: consumo {c} m³ excede máximo 5000")
        except ValueError:
            warnings.append("Metrogas: consumo no numérico")

    # Moneda ARS
    currency = _get_val(fields, "currency")
    if currency and str(currency).upper() != "ARS":
        errors.append(f"Metrogas: moneda debe ser ARS, encontrado: {currency}")

    return ValidationResult(is_consistent=len(errors) == 0, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# Factura Interna
# ---------------------------------------------------------------------------

def _validate_factura_interna(fields: Dict[str, ConciliationField]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    tolerance = 0.01

    subtotal = _get_val(fields, "subtotal")
    tax_amount = _get_val(fields, "tax_amount")
    tax_rate = _get_val(fields, "tax_rate")
    total = _get_val(fields, "total_amount")
    line_items = _get_val(fields, "line_items")

    # sum(line_items) = subtotal
    if line_items and isinstance(line_items, list) and subtotal is not None:
        try:
            items_sum = sum(float(item.get("amount", 0)) for item in line_items)
            subtotal_f = float(subtotal)
            if abs(items_sum - subtotal_f) > tolerance:
                errors.append(
                    f"Factura Interna: suma items ({items_sum:.2f}) ≠ subtotal ({subtotal_f:.2f})"
                )
        except (TypeError, ValueError, AttributeError):
            warnings.append("Factura Interna: no se pudo validar suma de items")

    # subtotal + tax = total
    if subtotal is not None and tax_amount is not None and total is not None:
        try:
            s = float(subtotal)
            t = float(tax_amount)
            tot = float(total)
            if abs(s + t - tot) > tolerance:
                errors.append(
                    f"Factura Interna: subtotal({s}) + tax({t}) = {s+t:.2f} ≠ total({tot})"
                )
        except (TypeError, ValueError):
            warnings.append("Factura Interna: no se pudo validar aritmética")

    # tax_rate en [0, 27]
    if tax_rate is not None:
        try:
            tr = float(tax_rate)
            if not (0 <= tr <= 27):
                errors.append(f"Factura Interna: tax_rate {tr}% fuera del rango [0, 27]")
        except (TypeError, ValueError):
            warnings.append("Factura Interna: tax_rate no numérico")

    # item count >= 1
    if line_items is not None and isinstance(line_items, list):
        if len(line_items) < 1:
            errors.append("Factura Interna: debe tener al menos 1 item")
        else:
            for i, item in enumerate(line_items):
                if isinstance(item, dict):
                    qty = item.get("quantity", 0)
                    price = item.get("unit_price", 0)
                    try:
                        if float(qty) <= 0:
                            errors.append(f"Item {i+1}: quantity debe ser > 0")
                        if float(price) <= 0:
                            errors.append(f"Item {i+1}: unit_price debe ser > 0")
                    except (TypeError, ValueError):
                        pass

    return ValidationResult(is_consistent=len(errors) == 0, errors=errors, warnings=warnings)


def merge_validation_results(results: List[ValidationResult]) -> ValidationResult:
    """Combina múltiples resultados de validación en uno."""
    all_errors = [e for r in results for e in r.errors]
    all_warnings = [w for r in results for w in r.warnings]
    return ValidationResult(
        is_consistent=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )
