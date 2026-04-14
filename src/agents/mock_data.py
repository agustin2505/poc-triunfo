"""Datos de demo realistas por proveedor para agentes mock."""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any, Dict, Tuple


def _rand_date(base: date, delta_days: int = 5) -> str:
    d = base + timedelta(days=random.randint(-delta_days, delta_days))
    return d.isoformat()


def _jitter(value: float, pct: float = 0.02) -> float:
    """Aplica variación aleatoria de ±pct al valor."""
    return round(value * (1 + random.uniform(-pct, pct)), 2)


def _confidence(base: float, spread: float = 0.08) -> float:
    return round(min(1.0, max(0.0, base + random.uniform(-spread, spread))), 3)


def edenor_fields(quality: str = "good") -> Dict[str, Tuple[Any, float]]:
    """Devuelve {campo: (valor, confidence)} para una factura Edenor."""
    today = date(2026, 3, 1)
    reading_start = random.randint(95000, 105000)
    consumption = random.randint(180, 320)
    reading_end = reading_start + consumption
    base_charge = round(random.uniform(1800, 2200), 2)
    consumption_charge = round(consumption * random.uniform(18, 22), 2)
    tax = round((base_charge + consumption_charge) * 0.21, 2)
    total = round(base_charge + consumption_charge + tax, 2)
    ref = f"0001-{random.randint(10000000, 99999999)}"

    conf_base = {"good": 0.93, "medium": 0.78, "poor": 0.61}[quality]

    return {
        "provider_name": ("Edenor", _confidence(conf_base + 0.03)),
        "issue_date": (_rand_date(today, 2), _confidence(conf_base)),
        "due_date": (_rand_date(today + timedelta(days=15), 2), _confidence(conf_base - 0.05)),
        "total_amount": (_jitter(total, 0.01 if quality == "good" else 0.04),
                         _confidence(conf_base)),
        "reference_number": (ref, _confidence(conf_base - 0.02)),
        "meter_reading_start": (str(reading_start), _confidence(conf_base - 0.04)),
        "meter_reading_end": (str(reading_end), _confidence(conf_base - 0.04)),
        "consumption": (consumption, _confidence(conf_base - 0.03)),
        "tariff_code": ("T1G", _confidence(conf_base - 0.06)),
        "currency": ("ARS", _confidence(conf_base + 0.05)),
        "period_start": (_rand_date(today - timedelta(days=31), 1), _confidence(conf_base - 0.05)),
        "period_end": (_rand_date(today - timedelta(days=1), 1), _confidence(conf_base - 0.05)),
    }


def metrogas_fields(quality: str = "good") -> Dict[str, Tuple[Any, float]]:
    today = date(2026, 3, 5)
    consumption = round(random.uniform(50, 450), 1)
    reading_start = round(random.uniform(5000, 15000), 1)
    reading_end = round(reading_start + consumption, 1)
    base_charge = round(random.uniform(800, 1200), 2)
    consumption_charge = round(consumption * random.uniform(12, 18), 2)
    tax = round((base_charge + consumption_charge) * 0.21, 2)
    total = round(base_charge + consumption_charge + tax, 2)
    ref = f"0004-{random.randint(10000000, 99999999)}"

    conf_base = {"good": 0.92, "medium": 0.76, "poor": 0.59}[quality]

    return {
        "provider_name": ("Metrogas", _confidence(conf_base + 0.03)),
        "issue_date": (_rand_date(today, 2), _confidence(conf_base)),
        "due_date": (_rand_date(today + timedelta(days=12), 2), _confidence(conf_base - 0.05)),
        "total_amount": (_jitter(total, 0.01 if quality == "good" else 0.04),
                         _confidence(conf_base)),
        "reference_number": (ref, _confidence(conf_base - 0.02)),
        "meter_reading_start": (str(reading_start), _confidence(conf_base - 0.04)),
        "meter_reading_end": (str(reading_end), _confidence(conf_base - 0.04)),
        "consumption": (consumption, _confidence(conf_base - 0.03)),
        "currency": ("ARS", _confidence(conf_base + 0.05)),
        "period_start": (_rand_date(today - timedelta(days=31), 1), _confidence(conf_base - 0.05)),
        "period_end": (_rand_date(today - timedelta(days=1), 1), _confidence(conf_base - 0.05)),
    }


def factura_interna_fields(quality: str = "good") -> Dict[str, Tuple[Any, float]]:
    today = date(2026, 3, 10)
    n_items = random.randint(2, 5)
    items = []
    subtotal = 0.0
    for i in range(n_items):
        qty = random.randint(1, 10)
        price = round(random.uniform(500, 5000), 2)
        items.append({"description": f"Servicio {i+1}", "quantity": qty,
                       "unit_price": price, "amount": round(qty * price, 2)})
        subtotal += qty * price
    subtotal = round(subtotal, 2)
    tax_rate = 21.0
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    ref = f"FC-{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"

    conf_base = {"good": 0.91, "medium": 0.74, "poor": 0.58}[quality]

    return {
        "provider_name": ("Nuestra Empresa", _confidence(conf_base + 0.03)),
        "issue_date": (_rand_date(today, 2), _confidence(conf_base)),
        "due_date": (_rand_date(today + timedelta(days=30), 3), _confidence(conf_base - 0.05)),
        "total_amount": (_jitter(total, 0.005 if quality == "good" else 0.03),
                         _confidence(conf_base)),
        "reference_number": (ref, _confidence(conf_base - 0.02)),
        "subtotal": (subtotal, _confidence(conf_base - 0.01)),
        "tax_amount": (tax_amount, _confidence(conf_base - 0.02)),
        "tax_rate": (tax_rate, _confidence(conf_base + 0.02)),
        "currency": ("ARS", _confidence(conf_base + 0.05)),
        "line_items": (items, _confidence(conf_base - 0.06)),
    }


PROVIDER_FIELD_GENERATORS = {
    "edenor-001": edenor_fields,
    "metrogas-001": metrogas_fields,
    "factura-interna-001": factura_interna_fields,
}

# Texto OCR simulado por proveedor (para el clasificador y Tesseract mock)
MOCK_RAW_TEXTS = {
    "edenor-001": (
        "EDENOR S.A.\nDistribuidora Eléctrica del Norte\n"
        "Factura de Luz - Servicio Eléctrico\n"
        "Cliente: Empresa Demo\nMedidor: 12345678\n"
        "Lectura Anterior: 100000 kWh\nLectura Actual: 100250 kWh\n"
        "Consumo: 250 kWh\nTarifa: T1G\n"
        "Cargo Básico: $2000.00\nCargo por Consumo: $5000.00\n"
        "IVA 21%: $1470.00\nTotal a Pagar: $8470.00\n"
        "Vencimiento: 15/03/2026\nNro. Factura: 0001-12345678"
    ),
    "metrogas-001": (
        "METROGAS S.A.\nGas Natural - Factura de Servicio\n"
        "Cliente: Empresa Demo\nCUIT: 20-12345678-1\n"
        "Medidor: 87654321\nLectura Anterior: 8500.0 m3\n"
        "Lectura Actual: 8750.5 m3\nConsumo: 250.5 m3\n"
        "Cargo Fijo: $1000.00\nCargo Variable: $3500.00\n"
        "IVA 21%: $945.00\nTotal: $5445.00\n"
        "Fecha Vencimiento: 20/03/2026\nNro. Factura: 0004-98765432"
    ),
    "factura-interna-001": (
        "NUESTRA EMPRESA S.R.L.\nFACTURA B Nro. FC-2026-001234\n"
        "Fecha: 10/03/2026\nCliente: Cliente Demo\n"
        "CUIT: 30-12345678-9\n"
        "Item 1: Servicio Consultoría - Qty: 2 - $5000.00 - $10000.00\n"
        "Item 2: Soporte Técnico - Qty: 5 - $1500.00 - $7500.00\n"
        "Subtotal: $17500.00\nIVA 21%: $3675.00\n"
        "Total: $21175.00\nVencimiento: 09/04/2026"
    ),
}
