"""Tests para la lógica de conciliación — Spec-11."""
import pytest
from src.models.document import AgentOutput, AgentStatus, AgentMetadata, FieldValue
from src.conciliation.conciliator import Conciliator


def make_output(agent_id: str, fields: dict, status: AgentStatus = AgentStatus.SUCCESS) -> AgentOutput:
    return AgentOutput(
        document_id="test-doc",
        agent_id=agent_id,
        status=status,
        duration_ms=100,
        fields={k: FieldValue(value=v[0], confidence=v[1]) for k, v in fields.items()},
        metadata=AgentMetadata(model_version="test-1.0"),
    )


@pytest.fixture
def conciliator():
    return Conciliator()


# ---------------------------------------------------------------------------
# Strings — mayoría simple
# ---------------------------------------------------------------------------

def test_string_majority(conciliator):
    outputs = {
        "docai": make_output("docai", {"provider_name": ("Edenor", 0.96)}),
        "tesseract": make_output("tesseract", {"provider_name": ("EDENOR", 0.88)}),
        "vertex": make_output("vertex", {"provider_name": ("Edenor", 0.94)}),
    }
    fields, score, routing, _ = conciliator.conciliate(outputs)
    pn = fields.get("provider_name")
    assert pn is not None
    assert "edenor" in str(pn.value).lower()
    assert pn.source == "majority"


def test_string_conflict_fallback_to_docai(conciliator):
    outputs = {
        "docai": make_output("docai", {"provider_name": ("Edenor", 0.92)}),
        "tesseract": make_output("tesseract", {"provider_name": ("Metrogas", 0.85)}),
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    pn = fields.get("provider_name")
    # Con dos agentes que discrepan, debe caer en fallback a docai
    assert pn is not None
    assert "edenor" in str(pn.value).lower()


def test_string_single_agent(conciliator):
    outputs = {
        "docai": make_output("docai", {"provider_name": ("Edenor", 0.95)}),
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    assert fields["provider_name"].value == "Edenor"
    assert fields["provider_name"].source == "docai"


# ---------------------------------------------------------------------------
# Numéricos
# ---------------------------------------------------------------------------

def test_numeric_within_tolerance(conciliator):
    """Todos dentro del 5% → promedio ponderado."""
    outputs = {
        "docai": make_output("docai", {"total_amount": (12345.67, 0.94)}),
        "tesseract": make_output("tesseract", {"total_amount": (12345.68, 0.92)}),
        "vertex": make_output("vertex", {"total_amount": (12345.70, 0.90)}),
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    ta = fields.get("total_amount")
    assert ta is not None
    assert abs(float(ta.value) - 12345.68) < 0.10  # cerca del promedio
    assert ta.source == "weighted_avg"


def test_numeric_high_deviation(conciliator):
    """Desviación > 5% → mayoría exacta."""
    outputs = {
        "docai": make_output("docai", {"total_amount": (10000.0, 0.90)}),
        "tesseract": make_output("tesseract", {"total_amount": (10000.0, 0.88)}),
        "vertex": make_output("vertex", {"total_amount": (5000.0, 0.85)}),  # outlier
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    ta = fields.get("total_amount")
    assert ta is not None
    assert float(ta.value) == 10000.0  # mayoría de 2 vs 1


def test_numeric_penalty_on_deviation(conciliator):
    """Desviación alta → penalización en confidence."""
    outputs = {
        "docai": make_output("docai", {"total_amount": (10000.0, 0.95)}),
        "tesseract": make_output("tesseract", {"total_amount": (5000.0, 0.90)}),
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    ta = fields.get("total_amount")
    # Confidence debe estar penalizada
    assert ta.confidence < 0.95


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

def test_date_majority(conciliator):
    outputs = {
        "docai": make_output("docai", {"issue_date": ("2026-03-01", 0.90)}),
        "tesseract": make_output("tesseract", {"issue_date": ("2026-03-01", 0.88)}),
        "vertex": make_output("vertex", {"issue_date": ("2026-03-05", 0.80)}),
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    d = fields.get("issue_date")
    assert d is not None
    assert d.value == "2026-03-01"
    assert d.source == "majority"


def test_date_no_majority_fallback(conciliator):
    outputs = {
        "docai": make_output("docai", {"issue_date": ("2026-03-01", 0.90)}),
        "tesseract": make_output("tesseract", {"issue_date": ("2026-03-02", 0.85)}),
    }
    fields, _, _, _ = conciliator.conciliate(outputs)
    d = fields.get("issue_date")
    # Fallback a docai
    assert d.value == "2026-03-01"


# ---------------------------------------------------------------------------
# Routing basado en confidence
# ---------------------------------------------------------------------------

def test_routing_auto_approve(conciliator):
    """Campos críticos con alta confidence → AUTO_APPROVE."""
    outputs = {
        "docai": make_output("docai", {
            "provider_name": ("Edenor", 0.96),
            "issue_date": ("2026-03-01", 0.92),
            "total_amount": (12345.67, 0.94),
        }),
        "tesseract": make_output("tesseract", {
            "provider_name": ("Edenor", 0.90),
            "issue_date": ("2026-03-01", 0.88),
            "total_amount": (12345.67, 0.92),
        }),
    }
    _, score, routing, _ = conciliator.conciliate(outputs)
    assert score >= 0.88
    assert routing.value == "AUTO_APPROVE"


def test_routing_hitl_standard(conciliator):
    """Confidence media → HITL_STANDARD."""
    outputs = {
        "docai": make_output("docai", {
            "provider_name": ("Edenor", 0.78),
            "issue_date": ("2026-03-01", 0.75),
            "total_amount": (12345.67, 0.76),
        }),
    }
    _, score, routing, _ = conciliator.conciliate(outputs)
    assert 0.70 <= score < 0.88
    assert routing.value == "HITL_STANDARD"


def test_routing_auto_reject_all_failed(conciliator):
    """Todos los agentes fallaron → AUTO_REJECT."""
    outputs = {
        "docai": make_output("docai", {}, status=AgentStatus.FAILED),
        "tesseract": make_output("tesseract", {}, status=AgentStatus.FAILED),
    }
    _, score, routing, _ = conciliator.conciliate(outputs)
    assert routing.value == "AUTO_REJECT"


def test_routing_hitl_priority_missing_critical(conciliator):
    """Campo crítico faltante → HITL_PRIORITY."""
    outputs = {
        "docai": make_output("docai", {
            "provider_name": ("Edenor", 0.96),
            # issue_date faltante
            "total_amount": (12345.67, 0.94),
        }),
    }
    _, score, routing, _ = conciliator.conciliate(outputs)
    assert routing.value == "HITL_PRIORITY"
