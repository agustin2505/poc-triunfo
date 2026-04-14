"""Agente A: Document AI (mock) — Spec-02."""
from __future__ import annotations

import random
from typing import Optional

from src.agents.base import BaseAgent
from src.agents.mock_data import PROVIDER_FIELD_GENERATORS
from src.models.document import AgentMetadata, AgentOutput, AgentStatus, FieldValue


class DocumentAIAgent(BaseAgent):
    """
    Motor principal de extracción. Mock realista que simula Document AI.
    Timeout: 15s. Fallback: si falla → Agente C.
    Success rate: 95%.
    """

    agent_id = "docai"
    timeout_ms = 15000

    def _extract(
        self,
        document_id: str,
        image_bytes: Optional[bytes],
        raw_text: Optional[str],
        provider_id: str = "edenor-001",
        quality: str = "good",
        **kwargs,
    ) -> AgentOutput:
        # Simular fallo aleatorio 5%
        if random.random() < 0.05:
            raise RuntimeError("DocumentAI service unavailable (simulated)")

        generator = PROVIDER_FIELD_GENERATORS.get(provider_id)
        if generator is None:
            generator = PROVIDER_FIELD_GENERATORS.get("edenor-001")

        fields_raw = generator(quality)

        # DocumentAI tiene la mejor accuracy — pequeña degradación para medium/poor
        confidence_multiplier = {"good": 1.0, "medium": 0.92, "poor": 0.80}[quality]
        fields = {}
        for name, (value, conf) in fields_raw.items():
            # Agregar pequeña variación aleatoria específica del agente
            adjusted_conf = round(min(1.0, conf * confidence_multiplier + random.uniform(-0.02, 0.02)), 3)
            fields[name] = FieldValue(value=value, confidence=adjusted_conf)

        # Simular latencia realista de Document AI
        import time
        time.sleep(random.uniform(0.05, 0.15))  # 50-150ms simulados

        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=0,  # será sobreescrito por base.run()
            fields=fields,
            raw_text=raw_text,
            metadata=AgentMetadata(
                model_version="docai-invoice-v2024-01",
                processing_region="us-east1",
            ),
        )
