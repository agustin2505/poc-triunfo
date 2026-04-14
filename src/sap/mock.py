"""SAP Mock — Spec-08."""
from __future__ import annotations

import random
import time
from collections import deque
from datetime import date, datetime, timezone
from typing import Any, Deque, Dict, Set, Tuple
import uuid


# Registro de documentos ya enviados a SAP (para detectar duplicados)
_SAP_REGISTRY: Set[str] = set()

# Ventana deslizante de requests en el último minuto (para simular rate limit)
_REQUEST_TIMESTAMPS: Deque[float] = deque()

RATE_LIMIT_PER_MINUTE = 100
SUCCESS_RATE = 0.95  # 5% de errores aleatorios


def post_to_sap(
    request_id: str,
    document_id: str,
    sede_id: str,
    provider: str,
    provider_id: str,
    reference_number: str,
    total_amount: float,
    currency: str,
    issue_date: str,
    sap_company_code: str = "AR00",
    sap_account_code: str = "6000",
    extracted_fields: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Envía documento al SAP mock. Implementa:
    - Detección de duplicados en memoria
    - Rate limiting (>100 req/min → INTERNAL_ERROR)
    - 5% de errores aleatorios
    - Respuestas según spec-08
    """
    now = time.time()

    # Rate limit check
    while _REQUEST_TIMESTAMPS and now - _REQUEST_TIMESTAMPS[0] > 60:
        _REQUEST_TIMESTAMPS.popleft()
    _REQUEST_TIMESTAMPS.append(now)

    if len(_REQUEST_TIMESTAMPS) > RATE_LIMIT_PER_MINUTE:
        return {
            "request_id": request_id,
            "status": "INTERNAL_ERROR",
            "message": "Error al procesar en SAP",
            "error_code": "SERVICE_UNAVAILABLE",
        }

    # Duplicate check
    dup_key = f"{str(reference_number).strip().lower()}|{provider.lower()}|{total_amount}"
    if dup_key in _SAP_REGISTRY:
        existing_doc = f"490{random.randint(1000000, 9999999)}"
        return {
            "request_id": request_id,
            "status": "DUPLICATE",
            "sap_document_number": existing_doc,
            "message": "Documento duplicado detectado",
            "existing_document": {
                "reference_number": reference_number,
                "provider": provider,
                "amount": total_amount,
                "posted_date": date.today().isoformat(),
            },
        }

    # Random error 5%
    if random.random() > SUCCESS_RATE:
        error_codes = ["TIMEOUT", "SERVICE_UNAVAILABLE", "UNKNOWN"]
        return {
            "request_id": request_id,
            "status": "INTERNAL_ERROR",
            "message": "Error al procesar en SAP",
            "error_code": random.choice(error_codes),
        }

    # Validation checks
    validation_errors = _sap_validate(total_amount, sap_account_code)
    if validation_errors:
        return {
            "request_id": request_id,
            "status": "VALIDATION_ERROR",
            "message": "Validación SAP fallida",
            "errors": validation_errors,
        }

    # SUCCESS
    sap_doc_number = f"49{random.randint(10000000, 99999999)}"
    _SAP_REGISTRY.add(dup_key)

    return {
        "request_id": request_id,
        "status": "SUCCESS",
        "sap_document_number": sap_doc_number,
        "sap_posting_date": date.today().isoformat(),
        "message": "Documento creado exitosamente en SAP",
        "audit": {
            "created_by": "TRIUNFO_SYSTEM",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _sap_validate(amount: float, account_code: str) -> list[str]:
    errors = []
    if amount > 999_999:
        errors.append("Monto excede límite permitido")
    VALID_ACCOUNTS = {"6000", "6001", "6100", "4000", "4100"}
    if account_code not in VALID_ACCOUNTS:
        errors.append(f"Código de cuenta inválido: {account_code}")
    return errors


def clear_sap_registry() -> None:
    """Para tests y demos."""
    _SAP_REGISTRY.clear()
    _REQUEST_TIMESTAMPS.clear()
