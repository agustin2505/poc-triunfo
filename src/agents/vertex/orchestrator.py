"""VertexOrchestrator — lanza los 3 agentes Gemini en paralelo — Spec-16."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
from typing import Dict, Optional

from src.agents.vertex.gemini_flash import GeminiFlashAgent
from src.agents.vertex.gemini_flash_lite import GeminiFlashLiteAgent
from src.agents.vertex.gemini_pro import GeminiProAgent
from src.logging_setup import setup_logging
from src.models.document import AgentMetadata, AgentOutput, AgentStatus, FieldValue

_logger = setup_logging("triunfo.agents.vertex_orchestrator")

_SELECTION_STRATEGIES = {"fastest_valid", "highest_confidence", "majority"}


class VertexOrchestrator:
    """Orquestador que corre GeminiFlashLite + GeminiFlash + GeminiPro en paralelo.

    Ocupa el lugar del Agente C (Vertex fallback) en processor.py.
    Se invoca solo cuando Agente A (DocumentAI) Y Agente B (Tesseract) fallan.
    """

    agent_id = "vertex-orchestrator"

    def __init__(self) -> None:
        self.flash_lite = GeminiFlashLiteAgent()
        self.flash = GeminiFlashAgent()
        self.pro = GeminiProAgent()
        self._agents = [self.flash_lite, self.flash, self.pro]

    # ------------------------------------------------------------------
    # Interfaz pública síncrona (compatible con processor.py)
    # ------------------------------------------------------------------

    def run_sync(
        self,
        document_id: str,
        image_bytes: Optional[bytes],
        provider_id: str = "edenor-001",
        quality: str = "good",
    ) -> AgentOutput:
        """Corre los 3 agentes en paralelo y retorna el mejor resultado."""
        timeout = int(os.getenv("VERTEX_PARALLEL_TIMEOUT", "120"))
        strategy = os.getenv("VERTEX_SELECTION_STRATEGY", "highest_confidence")
        if strategy not in _SELECTION_STRATEGIES:
            strategy = "highest_confidence"

        start = time.monotonic()
        results: Dict[str, AgentOutput] = {}
        durations: Dict[str, Optional[int]] = {a.agent_id: None for a in self._agents}

        _logger.info(
            f"[{document_id[:8]}] VertexOrchestrator iniciando "
            f"({len(self._agents)} agentes | strategy={strategy} | timeout={timeout}s)"
        )

        with ThreadPoolExecutor(max_workers=len(self._agents)) as executor:
            futures = {
                executor.submit(
                    agent.run,
                    document_id,
                    image_bytes=image_bytes,
                    provider_id=provider_id,
                    quality=quality,
                ): agent.agent_id
                for agent in self._agents
            }

            remaining_timeout = timeout - (time.monotonic() - start)
            try:
                for future in as_completed(futures, timeout=max(1.0, remaining_timeout)):
                    aid = futures[future]
                    try:
                        output = future.result()
                        results[aid] = output
                        durations[aid] = output.duration_ms
                        _logger.debug(
                            f"[{document_id[:8]}] {aid} completado: "
                            f"status={output.status.value} duration={output.duration_ms}ms"
                        )
                    except Exception as exc:
                        _logger.error(f"[{document_id[:8]}] {aid} excepción: {exc}")
                        results[aid] = AgentOutput(
                            document_id=document_id,
                            agent_id=aid,
                            status=AgentStatus.FAILED,
                            duration_ms=0,
                            metadata=AgentMetadata(model_version=f"{aid}-error"),
                        )
                        durations[aid] = 0
            except FutureTimeout:
                _logger.warning(
                    f"[{document_id[:8]}] VertexOrchestrator timeout global ({timeout}s). "
                    f"Resultados recibidos: {list(results.keys())}"
                )
                # Marcar agentes que no respondieron como TIMEOUT
                for aid in [futures[f] for f in futures if futures[f] not in results]:
                    results[aid] = AgentOutput(
                        document_id=document_id,
                        agent_id=aid,
                        status=AgentStatus.TIMEOUT,
                        duration_ms=timeout * 1000,
                        metadata=AgentMetadata(model_version=f"{aid}-timeout"),
                    )

        successful = {
            aid: out for aid, out in results.items()
            if out.status == AgentStatus.SUCCESS
        }

        if not successful:
            _logger.error(f"[{document_id[:8]}] VertexOrchestrator: todos los agentes fallaron")
            return self._failed_output(document_id, durations)

        selected = self._select(successful, strategy, document_id)
        selected = self._enrich_metadata(selected, results, strategy, durations)

        _logger.info(
            f"[{document_id[:8]}] VertexOrchestrator completado: "
            f"selected={selected.metadata.model_version} | "
            f"ok={len(successful)}/{len(self._agents)}"
        )
        return selected

    # Alias para compatibilidad con processor.py (que llama .run())
    def run(
        self,
        document_id: str,
        image_bytes: Optional[bytes] = None,
        raw_text: Optional[str] = None,
        **kwargs,
    ) -> AgentOutput:
        return self.run_sync(document_id, image_bytes=image_bytes, **kwargs)

    # ------------------------------------------------------------------
    # Estrategias de selección
    # ------------------------------------------------------------------

    def _select(
        self,
        successful: Dict[str, AgentOutput],
        strategy: str,
        document_id: str,
    ) -> AgentOutput:
        if strategy == "fastest_valid":
            # El que tenga menor duration_ms y al menos 3 campos no nulos
            valid = {
                aid: out for aid, out in successful.items()
                if sum(1 for f in out.fields.values() if f.value is not None) >= 3
            }
            pool = valid or successful
            return min(pool.values(), key=lambda o: o.duration_ms)

        if strategy == "majority":
            return self._majority_select(successful, document_id)

        # highest_confidence (default)
        def avg_conf(out: AgentOutput) -> float:
            if not out.fields:
                return 0.0
            return sum(f.confidence for f in out.fields.values()) / len(out.fields)

        return max(successful.values(), key=avg_conf)

    def _majority_select(
        self,
        successful: Dict[str, AgentOutput],
        document_id: str,
    ) -> AgentOutput:
        """Mini-conciliación: para cada campo, elige el valor más frecuente."""
        from collections import Counter

        all_field_names = set()
        for out in successful.values():
            all_field_names.update(out.fields.keys())

        merged_fields: Dict[str, FieldValue] = {}
        for fname in all_field_names:
            values = [
                (str(out.fields[fname].value), out.fields[fname].confidence)
                for out in successful.values()
                if fname in out.fields and out.fields[fname].value is not None
            ]
            if not values:
                merged_fields[fname] = FieldValue(value=None, confidence=0.0)
                continue

            counts = Counter(v for v, _ in values)
            best_val_str, _ = counts.most_common(1)[0]
            # Confidence promedio de los agentes que dieron ese valor
            confs = [c for v, c in values if v == best_val_str]
            avg_c = round(sum(confs) / len(confs), 3)
            # Recuperar el valor original (no el str) del primer agente que lo reportó
            original_value = best_val_str
            for out in successful.values():
                if fname in out.fields and str(out.fields[fname].value) == best_val_str:
                    original_value = out.fields[fname].value
                    break

            merged_fields[fname] = FieldValue(value=original_value, confidence=avg_c)

        # Retornar como AgentOutput sintético del orquestador
        best = max(successful.values(), key=lambda o: o.duration_ms * -1)  # el más rápido exitoso
        return AgentOutput(
            document_id=best.document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=max(o.duration_ms for o in successful.values()),
            fields=merged_fields,
            metadata=AgentMetadata(
                model_version="vertex-orchestrator-majority",
                processing_region=best.metadata.processing_region or "us-central1",
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _enrich_metadata(
        self,
        selected: AgentOutput,
        all_results: Dict[str, AgentOutput],
        strategy: str,
        durations: Dict[str, Optional[int]],
    ) -> AgentOutput:
        """Agrega metadata del orquestador al output seleccionado."""
        succeeded = [aid for aid, o in all_results.items() if o.status == AgentStatus.SUCCESS]
        failed = [aid for aid, o in all_results.items() if o.status != AgentStatus.SUCCESS]
        orchestrator_meta = {
            "orchestrator_strategy": strategy,
            "models_launched": [a.agent_id for a in self._agents],
            "models_succeeded": succeeded,
            "models_failed": failed,
            "selected_model": selected.metadata.model_version,
            "durations_ms": durations,
        }
        selected.metadata.model_version = (
            f"vertex-orchestrator-v1/{selected.metadata.model_version}"
        )
        # Guardamos info extra como JSON en raw_text si no hay otro uso
        selected.raw_text = json.dumps(orchestrator_meta)
        return selected

    def _failed_output(
        self,
        document_id: str,
        durations: Dict[str, Optional[int]],
    ) -> AgentOutput:
        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.FAILED,
            duration_ms=max((d or 0) for d in durations.values()),
            metadata=AgentMetadata(model_version="vertex-orchestrator-v1"),
        )
