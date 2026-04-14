"""Configuración de sedes — Spec-07."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TaxRates(BaseModel):
    iva: float = 21.0
    percepcion: float = 0.0
    otros: float = 0.0


class SedeConfig(BaseModel):
    sede_id: str
    sede_name: str
    location: str
    currency: str
    tax_context: str
    tax_rates: TaxRates
    enabled_providers: List[str]
    sap_company_code: str
    sap_chart_of_accounts: str
    hitl_sla_minutes: int
    upload_channels: List[str]
    active: bool = True
    created_at: str = "2026-04-01T00:00:00Z"
    updated_at: str = "2026-04-14T00:00:00Z"


SEDES: Dict[str, SedeConfig] = {
    "demo-001": SedeConfig(
        sede_id="demo-001",
        sede_name="Sede Buenos Aires",
        location="CABA, Argentina",
        currency="ARS",
        tax_context="AR_CONSUMER",
        tax_rates=TaxRates(iva=21.0, percepcion=0.0, otros=0.0),
        enabled_providers=["edenor-001", "metrogas-001", "factura-interna-001"],
        sap_company_code="AR00",
        sap_chart_of_accounts="AR",
        hitl_sla_minutes=120,
        upload_channels=["WEB"],
        active=True,
    ),
}


def get_sede(sede_id: str) -> Optional[SedeConfig]:
    return SEDES.get(sede_id)


DEFAULT_SEDE = "demo-001"
