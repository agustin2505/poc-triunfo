"""Contratos de datos del pipeline Triunfo — Spec-03."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentStatus(str, Enum):
    INGESTED = "INGESTED"
    CLASSIFIED = "CLASSIFIED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    CONCILIATED = "CONCILIATED"
    ROUTED = "ROUTED"


class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RoutingDecision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    HITL_STANDARD = "HITL_STANDARD"
    HITL_PRIORITY = "HITL_PRIORITY"
    AUTO_REJECT = "AUTO_REJECT"


class DocumentCategory(str, Enum):
    SERVICIOS = "SERVICIOS"
    FACTURA_NEGOCIO = "FACTURA_NEGOCIO"
    OTRO = "OTRO"


# ---------------------------------------------------------------------------
# Piezas base
# ---------------------------------------------------------------------------

class FieldValue(BaseModel):
    """Valor extraído por un agente para un campo dado."""
    value: Optional[Any] = None
    confidence: float = 0.0


class AgentMetadata(BaseModel):
    model_version: str = "mock-1.0"
    processing_region: Optional[str] = None
    field_count: int = 0
    fields_with_confidence_gt_0_85: int = 0


class AgentOutput(BaseModel):
    """Salida estándar de cualquier agente de extracción."""
    document_id: str
    agent_id: str
    status: AgentStatus
    duration_ms: int
    fields: Dict[str, FieldValue] = Field(default_factory=dict)
    raw_text: Optional[str] = None
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class ClassificationResult(BaseModel):
    """Resultado del Agente D (clasificador)."""
    category: DocumentCategory
    provider_id: str
    provider_name: str
    confidence: float


# ---------------------------------------------------------------------------
# Resultado de conciliación
# ---------------------------------------------------------------------------

class SourceDetail(BaseModel):
    value: Optional[Any] = None
    confidence: float = 0.0


class ConciliationField(BaseModel):
    """Campo conciliado entre múltiples agentes."""
    value: Optional[Any] = None
    confidence: float = 0.0
    source: str = "unknown"  # "majority", "agent_a", "agent_b", etc.
    sources_detail: Dict[str, SourceDetail] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    is_consistent: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline summary
# ---------------------------------------------------------------------------

class StageInfo(BaseModel):
    name: str
    duration_ms: int
    status: AgentStatus


class ProcessingSummary(BaseModel):
    total_duration_ms: int = 0
    stages: List[StageInfo] = Field(default_factory=list)
    models_used: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ingesta y resultado completo
# ---------------------------------------------------------------------------

class DocumentIngestion(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sede_id: str = "demo-001"
    source_channel: str = "web"
    uploaded_by: str = "demo@empresa.com"
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    mime_type: str = "image/jpeg"
    gcs_uri: Optional[str] = None
    file_size_bytes: int = 0
    file_name: str = ""


class DocumentResult(BaseModel):
    """Resultado completo del pipeline para un documento."""
    document_id: str
    status: DocumentStatus = DocumentStatus.INGESTED
    category: Optional[DocumentCategory] = None
    provider: Optional[str] = None
    provider_id: Optional[str] = None
    confidence_score: float = 0.0
    classification: Optional[ClassificationResult] = None
    agent_outputs: Dict[str, AgentOutput] = Field(default_factory=dict)
    extracted_fields: Dict[str, ConciliationField] = Field(default_factory=dict)
    validation: Optional[ValidationResult] = None
    routing: Optional[RoutingDecision] = None
    routing_reason: Optional[str] = None
    processing_summary: Optional[ProcessingSummary] = None
    sap_response: Optional[Dict] = None
    ingestion: Optional[DocumentIngestion] = None
