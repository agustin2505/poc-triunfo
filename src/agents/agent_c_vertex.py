"""Agente C: Vertex AI (fallback) — Spec-02."""
from __future__ import annotations

import random
from typing import Optional

from src.agents.base import BaseAgent
from src.agents.mock_data import PROVIDER_FIELD_GENERATORS
from src.models.document import AgentMetadata, AgentOutput, AgentStatus, FieldValue


class VertexAgent(BaseAgent):
    """
    Modelo generalista de fallback. Se invoca solo si Agente A falla.
    Timeout: 10s. Si también falla → AUTO_REJECT.
    Ligeramente menos preciso que DocumentAI.
    """

    agent_id = "vertex"
    timeout_ms = 10000

    def _extract(
        self,
        document_id: str,
        image_bytes: Optional[bytes],
        raw_text: Optional[str],
        provider_id: str = "edenor-001",
        quality: str = "good",
        **kwargs,
    ) -> AgentOutput:
        # Vertex falla con probabilidad ligeramente mayor (8%)
        if random.random() < 0.08:
            raise RuntimeError("Vertex AI service unavailable (simulated)")

        generator = PROVIDER_FIELD_GENERATORS.get(provider_id)
        if generator is None:
            generator = PROVIDER_FIELD_GENERATORS.get("edenor-001")

        fields_raw = generator(quality)

        # Vertex es bueno pero un poco menos preciso que DocumentAI
        conf_penalty = {"good": -0.03, "medium": -0.07, "poor": -0.12}[quality]
        fields: Dict[str, FieldValue] = {}

        from typing import Dict
        for name, (value, conf) in fields_raw.items():
            adjusted_conf = round(
                min(1.0, max(0.0, conf + conf_penalty + random.uniform(-0.03, 0.03))),
                3,
            )
            fields[name] = FieldValue(value=value, confidence=adjusted_conf)

        import time
        time.sleep(random.uniform(0.08, 0.20))

        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=0,
            fields=fields,
            raw_text=raw_text,
            metadata=AgentMetadata(
                model_version="vertex-gemini-1.5-flash",
                processing_region="us-central1",
            ),
        )
