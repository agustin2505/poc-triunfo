"""Agente Gemini 2.5 Pro (Vertex AI) — Spec-14."""
from __future__ import annotations

import os
import time
from typing import Optional

from src.agents.base import BaseAgent
from src.agents.vertex.prompts import (
    build_prompts,
    map_fase1_to_agent_fields,
    parse_json_response,
)
from src.logging_setup import setup_logging
from src.models.document import AgentMetadata, AgentOutput, AgentStatus

_logger = setup_logging("triunfo.agents.gemini_pro")

_RETRYABLE_CODES = {"RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL"}


class GeminiProAgent(BaseAgent):
    """Agente de alta precisión — gemini-2.5-pro-preview-05-06.

    Optimizado para facturas con layouts complejos o baja calidad de imagen.
    El más lento del trío: se usa como desempate cuando los modelos rápidos
    tienen baja confidence o resultados contradictorios.
    """

    agent_id = "gemini-pro"
    timeout_ms = 90000

    def __init__(self) -> None:
        self._model = None

    def _init_model(self) -> None:
        if self._model is not None:
            return

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except ImportError:
            raise RuntimeError(
                "google-cloud-aiplatform no está instalado. "
                "Ejecutar: pip install google-cloud-aiplatform"
            )

        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise RuntimeError(
                "Variable de entorno GOOGLE_CLOUD_PROJECT no configurada."
            )

        self._location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        model_id = os.getenv("GEMINI_PRO_MODEL", "gemini-2.0-pro-exp")

        vertexai.init(project=project, location=self._location)
        self._model = GenerativeModel(model_id)
        self._model_id = model_id
        _logger.info(f"GeminiProAgent inicializado: {model_id} @ {self._location}")

    def _extract(
        self,
        document_id: str,
        image_bytes: Optional[bytes],
        raw_text: Optional[str],
        provider_id: str = "edenor-001",
        quality: str = "good",
        **kwargs,
    ) -> AgentOutput:
        self._init_model()

        if not image_bytes:
            raise ValueError("GeminiProAgent requiere image_bytes")

        from vertexai.generative_models import GenerationConfig

        parts = build_prompts(image_bytes, "image/jpeg")
        gen_cfg = GenerationConfig(
            response_mime_type="application/json",
            temperature=0.0,
        )

        response = self._call_with_retry(parts, gen_cfg)
        fase1 = parse_json_response(response.text)
        fields = map_fase1_to_agent_fields(fase1)

        _logger.debug(
            f"[{document_id[:8]}] gemini-pro extrajo "
            f"{sum(1 for f in fields.values() if f.value is not None)} campos no nulos"
        )

        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=0,
            fields=fields,
            metadata=AgentMetadata(
                model_version=self._model_id,
                processing_region=self._location,
            ),
        )

    def _call_with_retry(self, parts, gen_cfg, max_retries: int = 2):
        """2 reintentos con backoff exponencial en errores retryable."""
        from google.api_core.exceptions import GoogleAPICallError

        for attempt in range(max_retries + 1):
            try:
                return self._model.generate_content(parts, generation_config=gen_cfg)
            except GoogleAPICallError as exc:
                code = getattr(exc, "code", None) or getattr(exc, "grpc_status_code", None)
                http_code = getattr(exc, "http_status", None)
                retryable = (
                    (str(code) in _RETRYABLE_CODES if code else False)
                    or (http_code in {429, 500, 503})
                )
                if retryable and attempt < max_retries:
                    wait = 2 ** attempt
                    _logger.warning(
                        f"gemini-pro error retryable (attempt {attempt+1}/{max_retries}): "
                        f"{exc}. Esperando {wait}s..."
                    )
                    time.sleep(wait)
                    continue
                raise
