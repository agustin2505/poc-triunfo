"""Tests unitarios para las validaciones genéricas y por proveedor — Spec-11."""
import pytest
from src.models.document import ConciliationField
from src.validation.generic import validate_generic, clear_duplicate_registry
from src.validation.provider_specific import validate_provider


def make_fields(**kwargs) -> dict:
    return {k: ConciliationField(value=v, confidence=0.9) for k, v in kwargs.items()}


@pytest.fixture(autouse=True)
def reset_registry():
    clear_duplicate_registry()
    yield
    clear_duplicate_registry()


# ---------------------------------------------------------------------------
# Validaciones genéricas — montos
# ---------------------------------------------------------------------------

def test_valid_total_amount():
    fields = make_fields(total_amount=1500.0, reference_number="REF-001", issue_date="2026-03-01")
    result = validate_generic(fields)
    assert result.is_consistent

def test_total_amount_zero():
    fields = make_fields(total_amount=0.0, reference_number="REF-001", issue_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent
    assert any("total_amount" in e for e in result.errors)

def test_total_amount_negative():
    fields = make_fields(total_amount=-500.0, reference_number="REF-001", issue_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent

def test_total_amount_exceeds_limit():
    fields = make_fields(total_amount=1_000_000.0, reference_number="REF-001", issue_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent
    assert any("999999" in e for e in result.errors)

def test_missing_total_amount():
    fields = make_fields(reference_number="REF-001", issue_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent
    assert any("total_amount" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Validaciones genéricas — fechas
# ---------------------------------------------------------------------------

def test_future_issue_date():
    fields = make_fields(total_amount=1000.0, reference_number="REF-001",
                         issue_date="2099-01-01")
    result = validate_generic(fields)
    assert not result.is_consistent
    assert any("futuro" in e.lower() for e in result.errors)

def test_due_date_before_issue_date():
    fields = make_fields(total_amount=1000.0, reference_number="REF-001",
                         issue_date="2026-03-15", due_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent
    assert any("anterior" in e.lower() for e in result.errors)

def test_missing_due_date_generates_warning():
    fields = make_fields(total_amount=1000.0, reference_number="REF-001",
                         issue_date="2026-03-01")
    result = validate_generic(fields)
    assert result.is_consistent
    assert any("due_date" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Validaciones genéricas — referencia
# ---------------------------------------------------------------------------

def test_reference_too_short():
    fields = make_fields(total_amount=1000.0, reference_number="AB1",
                         issue_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent

def test_reference_valid():
    fields = make_fields(total_amount=1000.0, reference_number="0001-00012345",
                         issue_date="2026-03-01")
    result = validate_generic(fields)
    assert result.is_consistent or all("reference" not in e for e in result.errors)

def test_reference_with_invalid_chars():
    fields = make_fields(total_amount=1000.0, reference_number="REF<script>",
                         issue_date="2026-03-01")
    result = validate_generic(fields)
    assert not result.is_consistent


# ---------------------------------------------------------------------------
# Validaciones genéricas — duplicados
# ---------------------------------------------------------------------------

def test_duplicate_detection():
    fields = make_fields(total_amount=1000.0, reference_number="REF-12345",
                         issue_date="2026-03-01")
    # Primera vez — ok
    r1 = validate_generic(fields, provider_name="Edenor")
    assert r1.is_consistent
    # Segunda vez — duplicado
    r2 = validate_generic(fields, provider_name="Edenor")
    assert not r2.is_consistent
    assert any("duplicado" in e.lower() for e in r2.errors)

def test_no_duplicate_different_ref():
    fields1 = make_fields(total_amount=1000.0, reference_number="REF-A", issue_date="2026-03-01")
    fields2 = make_fields(total_amount=1000.0, reference_number="REF-B", issue_date="2026-03-01")
    validate_generic(fields1, provider_name="Edenor")
    r2 = validate_generic(fields2, provider_name="Edenor")
    assert r2.is_consistent


# ---------------------------------------------------------------------------
# Validaciones genéricas — aritmética
# ---------------------------------------------------------------------------

def test_arithmetic_consistency():
    fields = make_fields(
        total_amount=121.0, subtotal=100.0, tax_amount=21.0,
        reference_number="REF-001", issue_date="2026-03-01"
    )
    result = validate_generic(fields)
    assert result.is_consistent

def test_arithmetic_inconsistency():
    fields = make_fields(
        total_amount=200.0, subtotal=100.0, tax_amount=21.0,
        reference_number="REF-001", issue_date="2026-03-01"
    )
    result = validate_generic(fields)
    assert not result.is_consistent


# ---------------------------------------------------------------------------
# Validaciones por proveedor — Edenor
# ---------------------------------------------------------------------------

def test_edenor_valid():
    fields = make_fields(
        meter_reading_start="100000", meter_reading_end="100250",
        consumption=250, tariff_code="T1G", currency="ARS"
    )
    result = validate_provider("edenor-001", fields)
    assert result.is_consistent

def test_edenor_reading_reversed():
    fields = make_fields(
        meter_reading_start="100300", meter_reading_end="100000",
        consumption=250, tariff_code="T1G", currency="ARS"
    )
    result = validate_provider("edenor-001", fields)
    assert not result.is_consistent

def test_edenor_consumption_over_limit():
    fields = make_fields(consumption=15000, tariff_code="T1G", currency="ARS")
    result = validate_provider("edenor-001", fields)
    assert not result.is_consistent

def test_edenor_wrong_currency():
    fields = make_fields(consumption=250, tariff_code="T1G", currency="USD")
    result = validate_provider("edenor-001", fields)
    assert not result.is_consistent


# ---------------------------------------------------------------------------
# Validaciones por proveedor — Metrogas
# ---------------------------------------------------------------------------

def test_metrogas_valid():
    fields = make_fields(consumption=200, currency="ARS")
    result = validate_provider("metrogas-001", fields)
    assert result.is_consistent

def test_metrogas_consumption_zero():
    fields = make_fields(consumption=0, currency="ARS")
    result = validate_provider("metrogas-001", fields)
    assert not result.is_consistent

def test_metrogas_overconsumption():
    fields = make_fields(consumption=6000, currency="ARS")
    result = validate_provider("metrogas-001", fields)
    assert not result.is_consistent


# ---------------------------------------------------------------------------
# Validaciones por proveedor — Factura Interna
# ---------------------------------------------------------------------------

def test_factura_interna_arithmetic_ok():
    line_items = [
        {"description": "Item 1", "quantity": 2, "unit_price": 5000, "amount": 10000},
        {"description": "Item 2", "quantity": 1, "unit_price": 3000, "amount": 3000},
    ]
    fields = make_fields(
        subtotal=13000.0, tax_amount=2730.0, tax_rate=21.0,
        total_amount=15730.0, line_items=line_items
    )
    result = validate_provider("factura-interna-001", fields)
    assert result.is_consistent

def test_factura_interna_items_sum_mismatch():
    line_items = [
        {"description": "Item 1", "quantity": 1, "unit_price": 1000, "amount": 1000},
    ]
    fields = make_fields(
        subtotal=5000.0, tax_amount=1050.0, tax_rate=21.0,
        total_amount=6050.0, line_items=line_items
    )
    result = validate_provider("factura-interna-001", fields)
    assert not result.is_consistent

def test_factura_interna_no_items():
    fields = make_fields(subtotal=1000.0, tax_amount=210.0, tax_rate=21.0,
                          total_amount=1210.0, line_items=[])
    result = validate_provider("factura-interna-001", fields)
    assert not result.is_consistent

def test_unknown_provider_passes():
    fields = make_fields(total_amount=1000.0)
    result = validate_provider("unknown-provider", fields)
    assert result.is_consistent
