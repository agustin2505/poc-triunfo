"""Agente Claude Vision (Anthropic SDK) — Spec-19."""
from __future__ import annotations

import os
import time
from typing import Optional

from src.agents.base import BaseAgent
from src.agents.prompts_imagen import (
    SCHEMA_FASE1,
    SYSTEM_PROMPT_FASE1,
    build_fase1_messages_claude,
    inject_schema,
    map_fase1_to_agent_fields,
    parse_json_response,
)
from src.logging_setup import setup_logging
from src.models.document import AgentMetadata, AgentOutput, AgentStatus

_logger = setup_logging("triunfo.agents.claude_vision")

_RETRY_STATUS_CODES = {429, 529}  # rate limit y overloaded


class ClaudeVisionAgent(BaseAgent):
    """Extracción multimodal con claude-sonnet-4-6 via Anthropic SDK.

    Usa prompt caching en el system prompt para reducir costo en
    procesamiento repetitivo de facturas (~90% ahorro en tokens de sistema).
    """

    agent_id = "claude-vision"
    timeout_ms = 30000

    def __init__(self) -> None:
        self._client = None

    # ------------------------------------------------------------------
    # Inicialización lazy
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        if self._client is not None:
            return

        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic SDK no está instalado. "
                "Ejecutar: pip install anthropic"
            )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Variable de entorno ANTHROPIC_API_KEY no configurada."
            )

        self._model_id = os.getenv("CLAUDE_VISION_MODEL", "claude-sonnet-4-6")
        self._max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))
        self._client = anthropic.Anthropic(api_key=api_key)
        _logger.info(f"ClaudeVisionAgent inicializado: {self._model_id}")

    # ------------------------------------------------------------------
    # Extracción
    # ------------------------------------------------------------------

    def _extract(
        self,
        document_id: str,
        image_bytes: Optional[bytes],
        raw_text: Optional[str],
        provider_id: str = "edenor-001",
        quality: str = "good",
        **kwargs,
    ) -> AgentOutput:
        self._init_client()

        if not image_bytes:
            raise ValueError("ClaudeVisionAgent requiere image_bytes")

        import base64
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        messages = build_fase1_messages_claude(image_b64, mime_type="image/jpeg")

        # System prompt con prompt caching: el bloque largo se cachea
        system_prompt_with_schema = inject_schema(
            SYSTEM_PROMPT_FASE1 + "\n\nSchema esperado:\n",
            SCHEMA_FASE1,
        )

        response, cache_hit = self._call_with_retry(
            messages=messages,
            system_prompt=system_prompt_with_schema,
        )

        raw_response_text = response.content[0].text
        fase1 = parse_json_response(raw_response_text)
        fields = map_fase1_to_agent_fields(fase1)

        # Leer métricas de uso
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        _logger.debug(
            f"[{document_id[:8]}] claude-vision extrajo "
            f"{sum(1 for f in fields.values() if f.value is not None)} campos no nulos | "
            f"cache_hit={cache_hit} | tokens={input_tokens}+{output_tokens}"
        )

        metadata = AgentMetadata(
            model_version=self._model_id,
            processing_region="anthropic-cloud",
        )
        # Guardar métricas extra en model_version temporalmente (compatible con AgentMetadata)
        # En una versión futura se puede extender AgentMetadata con campos extra
        if cache_hit:
            metadata.model_version = f"{self._model_id}[cache_hit]"

        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=0,
            fields=fields,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def _call_with_retry(self, messages, system_prompt: str, max_retries: int = 1):
        """1 reintento con backoff en errores 429 y 529 (overloaded)."""
        import anthropic

        # System prompt con cache_control para prompt caching
        system_with_cache = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        for attempt in range(max_retries + 1):
            try:
                response = self._client.messages.create(
                    model=self._model_id,
                    max_tokens=self._max_tokens,
                    system=system_with_cache,
                    messages=messages,
                )
                # Detectar cache hit: tokens en cache_read > 0
                usage = getattr(response, "usage", None)
                cache_read = getattr(usage, "cache_read_input_tokens", 0) if usage else 0
                cache_hit = (cache_read or 0) > 0
                return response, cache_hit

            except anthropic.APIStatusError as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code in _RETRY_STATUS_CODES and attempt < max_retries:
                    wait = 2 ** attempt
                    _logger.warning(
                        f"claude-vision HTTP {status_code} (attempt {attempt+1}). "
                        f"Reintentando en {wait}s..."
                    )
                    time.sleep(wait)
                    continue
                raise

            except anthropic.APIConnectionError as exc:
                if attempt < max_retries:
                    _logger.warning(f"claude-vision connection error (attempt {attempt+1}): {exc}")
                    time.sleep(2)
                    continue
                raise
