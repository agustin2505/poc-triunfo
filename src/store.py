"""Shared document store — usado por la API y el bot de Telegram."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Set

from src.logging_setup import setup_logging
from src.models.document import DocumentResult, RoutingDecision
from src.sap.mock import post_to_sap

logger = setup_logging("triunfo.store")

_documents: Dict[str, DocumentResult] = {}
_rejected_ids: Set[str] = set()


def save(result: DocumentResult) -> None:
    _documents[result.document_id] = result


def get(document_id: str) -> Optional[DocumentResult]:
    return _documents.get(document_id)


def all_documents() -> List[DocumentResult]:
    return list(_documents.values())


def count() -> int:
    return len(_documents)


def is_approved(document_id: str) -> bool:
    doc = _documents.get(document_id)
    return doc is not None and doc.sap_response is not None


def is_rejected(document_id: str) -> bool:
    return document_id in _rejected_ids


def approve(document_id: str) -> dict:
    """Aprueba el documento y lo envía al SAP mock. Lanza KeyError/ValueError en estado inválido."""
    doc = _documents.get(document_id)
    if doc is None:
        raise KeyError(f"Documento {document_id!r} no encontrado")
    if document_id in _rejected_ids:
        raise ValueError("El documento fue rechazado por el operador y no puede aprobarse")
    if doc.routing == RoutingDecision.AUTO_REJECT:
        raise ValueError("El documento fue rechazado automáticamente y no puede aprobarse")
    if doc.sap_response is not None:
        raise ValueError("El documento ya fue aprobado anteriormente")

    fields = doc.extracted_fields

    def _val(key, default=None):
        f = fields.get(key)
        return f.value if f else default

    from src.config.sede import get_sede
    sede = get_sede(doc.ingestion.sede_id if doc.ingestion else "demo-001")

    sap_response = post_to_sap(
        request_id=str(uuid.uuid4()),
        document_id=document_id,
        sede_id=doc.ingestion.sede_id if doc.ingestion else "demo-001",
        provider=doc.provider or "",
        provider_id=doc.provider_id or "",
        reference_number=str(_val("reference_number")) if _val("reference_number") else f"REF-{document_id[:8]}",
        total_amount=float(_val("total_amount", 0) or 0),
        currency=str(_val("currency", "ARS")),
        issue_date=str(_val("issue_date", "")),
        sap_company_code=sede.sap_company_code if sede else "AR00",
        extracted_fields={k: v.model_dump() for k, v in fields.items()},
    )

    doc.sap_response = sap_response
    _documents[document_id] = doc
    logger.info(f"Documento {document_id[:8]} aprobado y enviado a SAP")
    return sap_response


def reject(document_id: str) -> None:
    """Marca el documento como rechazado por el operador. Lanza KeyError si no existe."""
    if document_id not in _documents:
        raise KeyError(f"Documento {document_id!r} no encontrado")
    _rejected_ids.add(document_id)
    logger.info(f"Documento {document_id[:8]} rechazado por operador")


def reset() -> None:
    _documents.clear()
    _rejected_ids.clear()
