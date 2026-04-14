"""Catálogo de proveedores — Spec-06."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ProviderSchema(BaseModel):
    required: List[str]
    optional: List[str] = []


class ProviderConfig(BaseModel):
    provider_id: str
    provider_name: str
    category: str  # SERVICIOS | FACTURA_NEGOCIO | OTRO
    keywords: List[str]
    active: bool = True
    schema_fields: ProviderSchema
    validation_rules: Dict[str, Any]
    sap_mapping: Dict[str, str]


PROVIDERS: Dict[str, ProviderConfig] = {
    "edenor-001": ProviderConfig(
        provider_id="edenor-001",
        provider_name="Edenor",
        category="SERVICIOS",
        keywords=["edenor", "electricidad", "kwh", "factura luz", "medidor",
                  "distribuidora", "luz", "kw", "energia electrica", "distribuidora eléctrica"],
        schema_fields=ProviderSchema(
            required=["provider_name", "issue_date", "total_amount"],
            optional=["due_date", "reference_number", "meter_reading_start",
                      "meter_reading_end", "consumption", "tariff_code",
                      "period_start", "period_end"],
        ),
        validation_rules={
            "consumption_range": [0, 10000],
            "tax_rate": 21,
            "currency": "ARS",
        },
        sap_mapping={
            "provider_name": "VENDOR_CODE",
            "reference_number": "INVOICE_NO",
            "total_amount": "GROSS_AMOUNT",
            "issue_date": "DOCUMENT_DATE",
            "currency": "CURRENCY_KEY",
        },
    ),
    "metrogas-001": ProviderConfig(
        provider_id="metrogas-001",
        provider_name="Metrogas",
        category="SERVICIOS",
        keywords=["metrogas", "gas", "m3", "factura gas", "gasoducto",
                  "gas natural", "metro gas", "m³", "consumo gas"],
        schema_fields=ProviderSchema(
            required=["provider_name", "issue_date", "total_amount"],
            optional=["due_date", "reference_number", "consumption",
                      "meter_reading_start", "meter_reading_end",
                      "period_start", "period_end"],
        ),
        validation_rules={
            "consumption_range": [0, 5000],
            "tax_rate": [0, 27],
            "currency": "ARS",
        },
        sap_mapping={
            "provider_name": "VENDOR_CODE",
            "reference_number": "INVOICE_NO",
            "total_amount": "GROSS_AMOUNT",
            "issue_date": "DOCUMENT_DATE",
            "currency": "CURRENCY_KEY",
        },
    ),
    "factura-interna-001": ProviderConfig(
        provider_id="factura-interna-001",
        provider_name="Nuestra Empresa",
        category="FACTURA_NEGOCIO",
        keywords=["factura", "comprobante", "empresa", "venta", "servicio",
                  "nuestra empresa", "factura b", "factura a", "cuit",
                  "iva", "subtotal", "items"],
        schema_fields=ProviderSchema(
            required=["provider_name", "issue_date", "total_amount"],
            optional=["due_date", "reference_number", "subtotal",
                      "tax_amount", "tax_rate", "line_items"],
        ),
        validation_rules={
            "tax_rate": [0, 27],
            "currency": "ARS",
            "item_count_min": 1,
        },
        sap_mapping={
            "provider_name": "CUSTOMER_CODE",
            "reference_number": "SALES_ORDER",
            "total_amount": "GROSS_AMOUNT",
            "issue_date": "DOCUMENT_DATE",
            "currency": "CURRENCY_KEY",
        },
    ),
}


def get_provider(provider_id: str) -> Optional[ProviderConfig]:
    return PROVIDERS.get(provider_id)


def get_all_providers() -> List[ProviderConfig]:
    return [p for p in PROVIDERS.values() if p.active]


def find_provider_by_name(name: str) -> Optional[ProviderConfig]:
    name_lower = name.lower()
    for p in PROVIDERS.values():
        if p.provider_name.lower() in name_lower or name_lower in p.provider_name.lower():
            return p
    return None
