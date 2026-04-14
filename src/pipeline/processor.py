"""Orquestación del pipeline completo — Spec-02."""
from __future__ import annotations

import time
import uuid
from typing import Optional

from src.agents.agent_a_docai import DocumentAIAgent
from src.agents.agent_b_tesseract import TesseractAgent
from src.agents.agent_c_vertex import VertexAgent
from src.agents.agent_d_classifier import ClassifierAgent
from src.agents.agent_e_validator import ValidatorNormalizerAgent
from src.conciliation.conciliator import Conciliator
from src.logging_setup import setup_logging
from src.models.document import (
    AgentStatus, DocumentCategory, DocumentIngestion, DocumentResult,
    DocumentStatus, ProcessingSummary, RoutingDecision, StageInfo,
)
from src.validation.generic import validate_generic
from src.validation.provider_specific import merge_validation_results, validate_provider

logger = setup_logging("triunfo.pipeline")


class Pipeline:
    """
    Cadena de ejecución (Spec-02):
    1. Agente D (clasificador) — obligatorio
    2. Agentes A + B en paralelo (extracción)
    3. Si ambos fallan → Agente C (fallback)
    4. Agente E (normalización)
    5. Conciliación
    6. Validaciones genéricas + por proveedor
    7. Routing final
    """

    def __init__(self):
        self.classifier = ClassifierAgent()
        self.docai = DocumentAIAgent()
        self.tesseract = TesseractAgent()
        self.vertex = VertexAgent()
        self.normalizer = ValidatorNormalizerAgent()
        self.conciliator = Conciliator()

    def process(
        self,
        image_bytes: Optional[bytes],
        file_name: str = "",
        sede_id: str = "demo-001",
        uploaded_by: str = "demo@empresa.com",
        provider_hint: Optional[str] = None,
        quality_hint: str = "good",
    ) -> DocumentResult:
        pipeline_start = time.monotonic()
        document_id = str(uuid.uuid4())
        stages = []

        logger.info(f"[{document_id[:8]}] Pipeline iniciado | {file_name} | provider={provider_hint} | quality={quality_hint}")

        ingestion = DocumentIngestion(
            document_id=document_id,
            sede_id=sede_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_size_bytes=len(image_bytes) if image_bytes else 0,
            gcs_uri=f"gs://triunfo-demo/uploads/{document_id}.jpg",
        )

        result = DocumentResult(
            document_id=document_id,
            status=DocumentStatus.INGESTED,
            ingestion=ingestion,
        )

        # ------------------------------------------------------------------
        # Paso 1: Clasificación (Agente D)
        # ------------------------------------------------------------------
        logger.debug(f"[{document_id[:8]}] Iniciando clasificación...")
        t0 = time.monotonic()
        raw_text = None  # Tesseract lo obtiene en su propio paso

        # Para la clasificación usamos el hint o buscamos en el nombre de archivo
        # Si no hay raw_text, el clasificador intenta extraer de la imagen
        classification, classifier_output = self.classifier.classify(
            document_id=document_id,
            raw_text=raw_text or "",
            filename=file_name,
            provider_hint=provider_hint,
            image_bytes=image_bytes,
        )
        classif_ms = int((time.monotonic() - t0) * 1000)
        stages.append(StageInfo(name="classification", duration_ms=classif_ms,
                                status=classifier_output.status))
        result.agent_outputs["classifier"] = classifier_output

        logger.info(
            f"[{document_id[:8]}] Clasificación: {classification.provider_name} "
            f"({classification.category.value}) | confidence={classification.confidence:.2f}"
        )

        if classification.confidence < 0.40:
            logger.warning(
                f"[{document_id[:8]}] Clasificación con baja confidence ({classification.confidence:.2f}) "
                f"— usando proveedor por defecto para continuar extracción"
            )
            # En lugar de rechazar, usar un proveedor por defecto para siempre extraer datos
            from src.config.providers import PROVIDERS
            default_provider = next(iter(PROVIDERS.values()))
            classification.provider_id = default_provider.provider_id
            classification.provider_name = default_provider.provider_name
            classification.category = DocumentCategory(default_provider.category)
            classification.confidence = 0.42  # mínimo para seguir procesando

        result.status = DocumentStatus.CLASSIFIED
        result.category = classification.category
        result.provider = classification.provider_name
        result.provider_id = classification.provider_id
        result.classification = classification

        provider_id = classification.provider_id

        # ------------------------------------------------------------------
        # Paso 2: Extracción paralela A + B
        # ------------------------------------------------------------------
        result.status = DocumentStatus.PROCESSING

        t0 = time.monotonic()
        docai_output = self.docai.run(
            document_id=document_id,
            image_bytes=image_bytes,
            provider_id=provider_id,
            quality=quality_hint,
        )
        docai_ms = docai_output.duration_ms
        stages.append(StageInfo(name="docai", duration_ms=docai_ms,
                                status=docai_output.status))
        result.agent_outputs["docai"] = docai_output

        t0 = time.monotonic()
        tesseract_output = self.tesseract.run(
            document_id=document_id,
            image_bytes=image_bytes,
            provider_id=provider_id,
            quality=quality_hint,
        )
        tess_ms = tesseract_output.duration_ms
        stages.append(StageInfo(name="tesseract", duration_ms=tess_ms,
                                status=tesseract_output.status))
        result.agent_outputs["tesseract"] = tesseract_output

        # Capturar raw_text de Tesseract si tuvo éxito
        if tesseract_output.status == AgentStatus.SUCCESS:
            raw_text = tesseract_output.raw_text

        # ------------------------------------------------------------------
        # Paso 3: Fallback a Vertex si ambos A+B fallaron
        # ------------------------------------------------------------------
        a_ok = docai_output.status == AgentStatus.SUCCESS
        b_ok = tesseract_output.status == AgentStatus.SUCCESS
        vertex_output = None

        if not a_ok and not b_ok:
            t0 = time.monotonic()
            vertex_output = self.vertex.run(
                document_id=document_id,
                image_bytes=image_bytes,
                provider_id=provider_id,
                quality=quality_hint,
            )
            vtx_ms = vertex_output.duration_ms
            stages.append(StageInfo(name="vertex", duration_ms=vtx_ms,
                                    status=vertex_output.status))
            result.agent_outputs["vertex"] = vertex_output

            if vertex_output.status != AgentStatus.SUCCESS:
                result.status = DocumentStatus.ROUTED
                result.routing = RoutingDecision.AUTO_REJECT
                result.routing_reason = "Todos los agentes de extracción fallaron"
                result.processing_summary = ProcessingSummary(
                    total_duration_ms=int((time.monotonic() - pipeline_start) * 1000),
                    stages=stages,
                    missing_fields=["all"],
                )
                return result
        else:
            stages.append(StageInfo(name="vertex", duration_ms=0,
                                    status=AgentStatus.SKIPPED))

        result.status = DocumentStatus.EXTRACTED

        # ------------------------------------------------------------------
        # Paso 4: Normalización (Agente E)
        # ------------------------------------------------------------------
        # Unificar campos de los agentes que tuvieron éxito para normalizar
        all_fields = {}
        for aid, out in result.agent_outputs.items():
            if out.status == AgentStatus.SUCCESS and aid in ("docai", "tesseract", "vertex"):
                for fname, fv in out.fields.items():
                    if fname not in all_fields and fv.value is not None:
                        all_fields[fname] = fv

        t0 = time.monotonic()
        validator_output = self.normalizer.normalize(
            document_id=document_id,
            fields=all_fields,
        )
        val_ms = int((time.monotonic() - t0) * 1000)
        stages.append(StageInfo(name="validation_normalize", duration_ms=val_ms,
                                status=validator_output.status))
        result.agent_outputs["validator"] = validator_output

        # Propagar campos normalizados de vuelta a los outputs de los agentes
        # (para que la conciliación use valores ya normalizados)
        for aid in ("docai", "tesseract", "vertex"):
            out = result.agent_outputs.get(aid)
            if out and out.status == AgentStatus.SUCCESS:
                for fname, fv in out.fields.items():
                    if fname in validator_output.fields:
                        out.fields[fname] = validator_output.fields[fname]

        # ------------------------------------------------------------------
        # Paso 5: Conciliación
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        extracted_fields, confidence_score, routing, routing_reason = (
            self.conciliator.conciliate(result.agent_outputs)
        )
        concil_ms = int((time.monotonic() - t0) * 1000)
        stages.append(StageInfo(name="conciliation", duration_ms=concil_ms,
                                status=AgentStatus.SUCCESS))

        result.status = DocumentStatus.CONCILIATED
        result.extracted_fields = extracted_fields
        result.confidence_score = confidence_score

        # ------------------------------------------------------------------
        # Paso 6: Validaciones
        # ------------------------------------------------------------------
        generic_val = validate_generic(extracted_fields, provider_name=result.provider or "")
        provider_val = validate_provider(provider_id, extracted_fields)
        final_val = merge_validation_results([generic_val, provider_val])
        result.validation = final_val
        result.status = DocumentStatus.VALIDATED

        # Ajustar routing por validaciones
        if final_val.errors:
            if routing == RoutingDecision.AUTO_APPROVE:
                routing = RoutingDecision.HITL_PRIORITY
                routing_reason = f"Validación fallida: {final_val.errors[0]}"
                confidence_score -= 0.10
        elif final_val.warnings:
            if routing == RoutingDecision.AUTO_APPROVE and confidence_score < 0.92:
                routing = RoutingDecision.HITL_STANDARD
                routing_reason = f"Warnings presentes: {len(final_val.warnings)}"
            confidence_score -= 0.05

        result.confidence_score = round(max(0.0, confidence_score), 3)
        result.routing = routing
        result.routing_reason = routing_reason
        result.status = DocumentStatus.ROUTED

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        models_used = [
            aid for aid in ("docai", "tesseract", "vertex")
            if result.agent_outputs.get(aid) and
            result.agent_outputs[aid].status == AgentStatus.SUCCESS
        ]
        missing = [
            fname for fname, cf in extracted_fields.items()
            if cf.value is None
        ]

        result.processing_summary = ProcessingSummary(
            total_duration_ms=int((time.monotonic() - pipeline_start) * 1000),
            stages=stages,
            models_used=models_used,
            missing_fields=missing,
        )

        logger.info(
            f"[{document_id[:8]}] Pipeline completado: "
            f"{result.routing.value} | confidence={result.confidence_score:.2f} | "
            f"duration={result.processing_summary.total_duration_ms}ms | "
            f"models={','.join(models_used) or 'none'}"
        )

        return result
