"""ImageOrchestrator — Claude + 3 Gemini en paralelo para imágenes — Spec-20."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.agents.claude_vision import ClaudeVisionAgent
from src.agents.vertex.gemini_flash import GeminiFlashAgent
from src.agents.vertex.gemini_flash_lite import GeminiFlashLiteAgent
from src.agents.vertex.gemini_pro import GeminiProAgent
from src.logging_setup import setup_logging
from src.models.document import (
    AgentMetadata, AgentOutput, AgentStatus,
    ConciliationField, FieldValue, RoutingDecision,
)

_logger = setup_logging("triunfo.agents.image_orchestrator")

# Thresholds de confianza (sobreescribibles por env vars)
_DEFAULT_THRESHOLD_CRITICO = 0.90
_CRITICAL_FIELDS = {"total_amount", "supplier_cuit", "issue_date", "reference_number"}

# Weights de conciliación por agente
_DEFAULT_WEIGHTS = {
    "claude-vision": 0.35,
    "gemini-flash": 0.30,
    "gemini-pro": 0.25,
    "gemini-flash-lite": 0.10,
}


@dataclass
class OrchestratorResult:
    document_id: str
    status: str                                    # SUCCESS | PARTIAL | TIMEOUT | FAILED
    fase1_conciliado: Dict[str, ConciliationField] = field(default_factory=dict)
    sap_payload: Optional[Dict] = None
    routing: str = RoutingDecision.HITL_PRIORITY.value
    confidence_score_global: float = 0.0
    models_launched: List[str] = field(default_factory=list)
    models_succeeded: List[str] = field(default_factory=list)
    models_failed: List[str] = field(default_factory=list)
    durations_ms: Dict[str, Optional[int]] = field(default_factory=dict)
    fase2_trazabilidad: Optional[Dict] = None
    advertencias: List[str] = field(default_factory=list)


class ImageOrchestrator:
    """Orquestador multi-modelo para extracción desde imagen.

    Ejecuta Claude Vision + GeminiFlashLite + GeminiFlash + GeminiPro en
    paralelo (Fase 1), concilia los resultados con pesos configurables, y
    opcionalmente ejecuta Fase 2 (mapeo SAP via Claude).

    Se activa en processor.py cuando mime_type comienza con 'image/'.
    """

    def __init__(self) -> None:
        self.claude = ClaudeVisionAgent()
        self.flash_lite = GeminiFlashLiteAgent()
        self.flash = GeminiFlashAgent()
        self.pro = GeminiProAgent()
        self._agents = [self.claude, self.flash_lite, self.flash, self.pro]

    # ------------------------------------------------------------------
    # Interfaz pública — para processor.py
    # ------------------------------------------------------------------

    def run_sync(
        self,
        document_id: str,
        image_bytes: bytes,
        provider_id: str = "edenor-001",
        quality: str = "good",
        run_fase2: bool = False,
    ) -> OrchestratorResult:
        """Corre extracción paralela y retorna OrchestratorResult."""
        timeout = int(os.getenv("IMAGEN_PARALLEL_TIMEOUT", "120"))
        min_ok = int(os.getenv("IMAGEN_MIN_AGENTS_OK", "1"))
        threshold = float(os.getenv("THRESHOLD_CRITICO", str(_DEFAULT_THRESHOLD_CRITICO)))
        weights = self._load_weights()

        models_launched = [a.agent_id for a in self._agents]
        durations: Dict[str, Optional[int]] = {a.agent_id: None for a in self._agents}
        agent_outputs: Dict[str, AgentOutput] = {}
        advertencias: List[str] = []

        _logger.info(
            f"[{document_id[:8]}] ImageOrchestrator iniciando "
            f"({len(self._agents)} agentes | timeout={timeout}s)"
        )

        start = time.monotonic()

        # ------------------------------------------------------------------
        # Fase 1 — extracción paralela
        # ------------------------------------------------------------------
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

            remaining = timeout - (time.monotonic() - start)
            try:
                for future in as_completed(futures, timeout=max(1.0, remaining)):
                    aid = futures[future]
                    try:
                        output = future.result()
                        agent_outputs[aid] = output
                        durations[aid] = output.duration_ms
                        _logger.debug(
                            f"[{document_id[:8]}] {aid} "
                            f"status={output.status.value} "
                            f"duration={output.duration_ms}ms"
                        )
                    except Exception as exc:
                        _logger.error(f"[{document_id[:8]}] {aid} excepción: {exc}")
                        agent_outputs[aid] = AgentOutput(
                            document_id=document_id,
                            agent_id=aid,
                            status=AgentStatus.FAILED,
                            duration_ms=0,
                            metadata=AgentMetadata(model_version=f"{aid}-error"),
                        )
                        durations[aid] = 0
            except FutureTimeout:
                _logger.warning(
                    f"[{document_id[:8]}] ImageOrchestrator timeout global. "
                    f"Recibidos: {list(agent_outputs.keys())}"
                )
                for aid in [futures[f] for f in futures if futures[f] not in agent_outputs]:
                    agent_outputs[aid] = AgentOutput(
                        document_id=document_id,
                        agent_id=aid,
                        status=AgentStatus.TIMEOUT,
                        duration_ms=timeout * 1000,
                        metadata=AgentMetadata(model_version=f"{aid}-timeout"),
                    )
                    advertencias.append(f"Agente {aid} alcanzó el timeout global")

        successful = {
            aid: out for aid, out in agent_outputs.items()
            if out.status == AgentStatus.SUCCESS
        }
        models_succeeded = list(successful.keys())
        models_failed = [
            aid for aid, out in agent_outputs.items()
            if out.status != AgentStatus.SUCCESS
        ]

        if len(successful) < min_ok:
            _logger.error(
                f"[{document_id[:8]}] ImageOrchestrator: solo {len(successful)} agentes OK "
                f"(mínimo requerido: {min_ok}) → AUTO_REJECT"
            )
            return OrchestratorResult(
                document_id=document_id,
                status="FAILED",
                routing=RoutingDecision.AUTO_REJECT.value,
                models_launched=models_launched,
                models_succeeded=models_succeeded,
                models_failed=models_failed,
                durations_ms=durations,
                advertencias=advertencias + ["Todos los agentes fallaron o no alcanzaron el mínimo"],
            )

        # ------------------------------------------------------------------
        # Conciliación ponderada
        # ------------------------------------------------------------------
        conciliado = self._conciliate(successful, weights)
        confidence_global = self._confidence_global(conciliado)
        routing = self._determine_routing(conciliado, threshold)

        orch_status = "SUCCESS" if len(successful) == len(self._agents) else "PARTIAL"

        # ------------------------------------------------------------------
        # Fase 2 — Mapeo SAP (opcional, ejecuta solo si se solicita)
        # ------------------------------------------------------------------
        sap_payload = None
        fase2_trazabilidad = None

        if run_fase2:
            sap_payload, fase2_trazabilidad, fase2_warning = self._run_fase2(
                document_id, conciliado
            )
            if fase2_warning:
                advertencias.append(fase2_warning)
                if routing == RoutingDecision.AUTO_APPROVE.value:
                    routing = RoutingDecision.HITL_PRIORITY.value

        _logger.info(
            f"[{document_id[:8]}] ImageOrchestrator completado: "
            f"routing={routing} | confidence={confidence_global:.2f} | "
            f"ok={len(successful)}/{len(self._agents)}"
        )

        return OrchestratorResult(
            document_id=document_id,
            status=orch_status,
            fase1_conciliado=conciliado,
            sap_payload=sap_payload,
            routing=routing,
            confidence_score_global=confidence_global,
            models_launched=models_launched,
            models_succeeded=models_succeeded,
            models_failed=models_failed,
            durations_ms=durations,
            fase2_trazabilidad=fase2_trazabilidad,
            advertencias=advertencias,
        )

    def agent_outputs_from_result(self, result: OrchestratorResult) -> Dict[str, AgentOutput]:
        """Convierte el resultado conciliado a Dict[str, AgentOutput] para el Conciliator."""
        # Construye un AgentOutput sintético a partir del resultado conciliado
        fields = {
            fname: FieldValue(value=cf.value, confidence=cf.confidence)
            for fname, cf in result.fase1_conciliado.items()
        }
        synthetic = AgentOutput(
            document_id=result.document_id,
            agent_id="image-orchestrator",
            status=AgentStatus.SUCCESS if result.status in ("SUCCESS", "PARTIAL") else AgentStatus.FAILED,
            duration_ms=max((v or 0) for v in result.durations_ms.values()),
            fields=fields,
            metadata=AgentMetadata(
                model_version="image-orchestrator-v1",
                processing_region="multi-cloud",
            ),
        )
        return {"image-orchestrator": synthetic}

    # ------------------------------------------------------------------
    # Conciliación ponderada
    # ------------------------------------------------------------------

    def _conciliate(
        self,
        successful: Dict[str, AgentOutput],
        weights: Dict[str, float],
    ) -> Dict[str, ConciliationField]:
        """Concilia resultados de múltiples agentes con pesos configurables."""
        from collections import defaultdict
        from src.models.document import SourceDetail

        all_fields: set = set()
        for out in successful.values():
            all_fields.update(out.fields.keys())

        result: Dict[str, ConciliationField] = {}

        for fname in all_fields:
            sources: Dict[str, SourceDetail] = {}
            weighted_vals: Dict[str, float] = {}  # valor_str -> peso acumulado
            val_conf: Dict[str, list] = {}         # valor_str -> [conf]

            for aid, out in successful.items():
                fv = out.fields.get(fname)
                if fv is None or fv.value is None:
                    continue
                w = weights.get(aid, 0.10)
                val_str = str(fv.value)
                weighted_vals[val_str] = weighted_vals.get(val_str, 0.0) + w * fv.confidence
                val_conf.setdefault(val_str, []).append(fv.confidence)
                sources[aid] = SourceDetail(value=fv.value, confidence=fv.confidence)

            if not weighted_vals:
                result[fname] = ConciliationField(
                    value=None, confidence=0.0,
                    source="none", sources_detail=sources,
                )
                continue

            best_str = max(weighted_vals, key=weighted_vals.__getitem__)
            avg_conf = round(sum(val_conf[best_str]) / len(val_conf[best_str]), 3)

            # Recuperar valor original (no el str)
            original_value = best_str
            for out in successful.values():
                fv = out.fields.get(fname)
                if fv and str(fv.value) == best_str:
                    original_value = fv.value
                    break

            # Si hay discrepancia entre agentes → penalizar
            n_distinct = len(weighted_vals)
            if n_distinct > 1:
                avg_conf = round(avg_conf * 0.92, 3)

            num_supporters = len([v for v in val_conf[best_str]])
            source = "weighted_majority" if num_supporters > 1 else sources and next(iter(sources))

            result[fname] = ConciliationField(
                value=original_value,
                confidence=avg_conf,
                source=source or "weighted",
                sources_detail=sources,
            )

        return result

    # ------------------------------------------------------------------
    # Routing por thresholds
    # ------------------------------------------------------------------

    def _confidence_global(self, conciliado: Dict[str, ConciliationField]) -> float:
        critical = [
            conciliado[f].confidence
            for f in _CRITICAL_FIELDS
            if f in conciliado and conciliado[f].value is not None
        ]
        if not critical:
            return 0.0
        return round(sum(critical) / len(critical), 3)

    def _determine_routing(
        self,
        conciliado: Dict[str, ConciliationField],
        threshold: float,
    ) -> str:
        for fname in _CRITICAL_FIELDS:
            cf = conciliado.get(fname)
            if cf is None or cf.value is None:
                return RoutingDecision.HITL_PRIORITY.value
            if cf.confidence < 0.70:
                return RoutingDecision.HITL_PRIORITY.value
            if cf.confidence < threshold:
                return RoutingDecision.HITL_STANDARD.value

        return RoutingDecision.AUTO_APPROVE.value

    # ------------------------------------------------------------------
    # Fase 2 — Mapeo SAP via Claude
    # ------------------------------------------------------------------

    def _run_fase2(
        self,
        document_id: str,
        conciliado: Dict[str, ConciliationField],
    ):
        """Ejecuta Fase 2: JSON conciliado → payload SAP via Claude."""
        from src.agents.prompts_imagen import (
            SCHEMA_FASE2,
            SYSTEM_PROMPT_FASE2,
            build_fase2_messages_claude,
            inject_schema,
            parse_json_response,
        )
        import anthropic

        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return None, None, "ANTHROPIC_API_KEY no configurada — Fase 2 omitida"

            model_id = os.getenv("CLAUDE_VISION_MODEL", "claude-sonnet-4-6")
            client = anthropic.Anthropic(api_key=api_key)

            # Serializar el resultado conciliado como JSON de Fase 1
            fase1_serialized = json.dumps(
                {fname: {"value": cf.value, "confidence": cf.confidence}
                 for fname, cf in conciliado.items()},
                ensure_ascii=False,
                indent=2,
            )

            messages = build_fase2_messages_claude(fase1_serialized)
            system_prompt = inject_schema(
                SYSTEM_PROMPT_FASE2 + "\n\nSchema esperado:\n",
                SCHEMA_FASE2,
            )

            response = client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            )
            result_dict = parse_json_response(response.content[0].text)
            sap_payload = result_dict.get("sap_payload")
            trazabilidad = result_dict.get("trazabilidad")
            _logger.debug(f"[{document_id[:8]}] Fase 2 completada: {trazabilidad}")
            return sap_payload, trazabilidad, None

        except Exception as exc:
            _logger.error(f"[{document_id[:8]}] Fase 2 falló: {exc}")
            return None, None, f"Fase 2 falló: {exc}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_weights() -> Dict[str, float]:
        """Lee weights desde env vars, con defaults de la spec."""
        return {
            "claude-vision": float(os.getenv("WEIGHT_CLAUDE", str(_DEFAULT_WEIGHTS["claude-vision"]))),
            "gemini-flash": float(os.getenv("WEIGHT_GEMINI_FLASH", str(_DEFAULT_WEIGHTS["gemini-flash"]))),
            "gemini-pro": float(os.getenv("WEIGHT_GEMINI_PRO", str(_DEFAULT_WEIGHTS["gemini-pro"]))),
            "gemini-flash-lite": float(os.getenv("WEIGHT_GEMINI_FLASH_LITE", str(_DEFAULT_WEIGHTS["gemini-flash-lite"]))),
        }
