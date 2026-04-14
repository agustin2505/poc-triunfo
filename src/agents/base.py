"""Clase base para todos los agentes de extracción."""
from __future__ import annotations

import time
import traceback
from abc import ABC, abstractmethod
from typing import Optional

from src.models.document import AgentOutput, AgentStatus, AgentMetadata
from src.logging_setup import setup_logging

_logger = setup_logging("triunfo.agents")


class BaseAgent(ABC):
    """Agente base con manejo de timeout, logging y métricas."""

    agent_id: str
    timeout_ms: int

    def run(self, document_id: str, image_bytes: Optional[bytes] = None,
            raw_text: Optional[str] = None, **kwargs) -> AgentOutput:
        start = time.monotonic()
        try:
            result = self._extract(document_id, image_bytes, raw_text, **kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
            if elapsed > self.timeout_ms:
                _logger.warning(f"[{document_id[:8]}] Agente {self.agent_id} TIMEOUT ({elapsed}ms > {self.timeout_ms}ms)")
                return self._timeout_output(document_id, elapsed)
            result.duration_ms = elapsed
            result.metadata.field_count = len(result.fields)
            result.metadata.fields_with_confidence_gt_0_85 = sum(
                1 for f in result.fields.values() if f.confidence >= 0.85
            )
            _logger.debug(f"[{document_id[:8]}] Agente {self.agent_id} OK: {len(result.fields)} campos en {elapsed}ms")
            return result
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            _logger.error(f"[{document_id[:8]}] Agente {self.agent_id} FAILED: {e}")
            _logger.error(traceback.format_exc())
            return AgentOutput(
                document_id=document_id,
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                duration_ms=elapsed,
                metadata=AgentMetadata(model_version=f"{self.agent_id}-error"),
            )

    def _timeout_output(self, document_id: str, elapsed: int) -> AgentOutput:
        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.TIMEOUT,
            duration_ms=elapsed,
            metadata=AgentMetadata(model_version=f"{self.agent_id}-timeout"),
        )

    @abstractmethod
    def _extract(self, document_id: str, image_bytes: Optional[bytes],
                 raw_text: Optional[str], **kwargs) -> AgentOutput:
        ...
