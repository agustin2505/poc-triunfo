"""API FastAPI para el MVP Triunfo."""
from __future__ import annotations

import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src import store
from src.models.document import DocumentResult
from src.pipeline.processor import Pipeline
from src.logging_setup import setup_logging, get_memory_logs

logger = setup_logging("triunfo.api")

_pipeline = Pipeline()
_telegram_bot = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_bot
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        try:
            from src.telegram_bot.bot import TelegramBot
            _telegram_bot = TelegramBot()
            await _telegram_bot.initialize(app)
        except Exception:
            logger.warning("Bot de Telegram no pudo iniciarse:\n" + traceback.format_exc())
    else:
        logger.info("TELEGRAM_BOT_TOKEN no configurado — bot deshabilitado")
    yield
    if _telegram_bot:
        await _telegram_bot.shutdown()


app = FastAPI(
    title="Triunfo — MVP OCR/IDP",
    description="Pipeline de extracción de facturas con 5 agentes y conciliación por mayoría",
    version="1.0.0",
    lifespan=lifespan,
)

logger.info("=== Triunfo API iniciando ===")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "pipeline": "healthy",
            "docai_mock": "healthy",
            "tesseract_mock": "healthy",
            "vertex_mock": "healthy",
            "sap_mock": "healthy",
        },
    }


@app.post("/upload", summary="Subir y procesar factura (imagen o PDF)")
async def upload_document(
    file: UploadFile = File(...),
    provider_hint: Optional[str] = Form(None),
    quality_hint: str = Form("good"),
    sede_id: str = Form("demo-001"),
    uploaded_by: str = Form("demo@empresa.com"),
):
    """
    Procesa una imagen o PDF de factura a través del pipeline completo.

    - **file**: Imagen JPEG/PNG o PDF (texto o escaneado)
    - **provider_hint**: Forzar proveedor (edenor-001 | metrogas-001 | factura-interna-001)
    - **quality_hint**: Calidad simulada del documento (good | medium | poor)
    - **sede_id**: ID de sede (default: demo-001)
    """
    logger.info(f"Upload iniciado: {file.filename} ({file.content_type})")

    try:
        if not file.content_type:
            logger.error("Tipo de archivo no detectado")
            raise HTTPException(status_code=400, detail="Tipo de archivo no detectado")

        content_type = file.content_type.lower()
        allowed_image_types = {"image/jpeg", "image/jpg", "image/png", "image/tiff"}
        allowed_pdf_type = "application/pdf"

        if content_type not in allowed_image_types and content_type != allowed_pdf_type:
            logger.error(f"Tipo no soportado: {content_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no soportado. Use JPEG, PNG o PDF.",
            )

        if quality_hint not in ("good", "medium", "poor"):
            logger.error(f"Quality hint inválido: {quality_hint}")
            raise HTTPException(
                status_code=400,
                detail="quality_hint debe ser: good | medium | poor",
            )

        file_bytes = await file.read()
        logger.info(f"Archivo leído: {len(file_bytes)} bytes")

        if not file_bytes:
            logger.error("Archivo vacío")
            raise HTTPException(status_code=400, detail="Archivo vacío")

        image_bytes = file_bytes

        # Si es PDF, extraer texto
        if content_type == allowed_pdf_type:
            logger.info("Procesando PDF...")
            from src.pdf_handler import extract_from_pdf
            raw_text, page_images = extract_from_pdf(file_bytes)
            logger.info(f"PDF: {len(raw_text)} chars extraídos, {len(page_images)} imágenes")
            # Usar primera página como imagen si disponible
            if page_images:
                image_bytes = page_images[0]
                logger.info(f"Usando primera página: {len(image_bytes)} bytes")
            else:
                # PDF sin imágenes extraídas, usar placeholder
                image_bytes = b"\xff\xd8\xff"
                logger.info("Usando placeholder JPEG")

        logger.info(f"Iniciando pipeline con provider_hint={provider_hint}, quality={quality_hint}")
        result = _pipeline.process(
            image_bytes=image_bytes,
            file_name=file.filename or "documento",
            sede_id=sede_id,
            uploaded_by=uploaded_by,
            provider_hint=provider_hint,
            quality_hint=quality_hint,
            mime_type=content_type,
        )

        logger.info(
            f"Pipeline completado: {result.document_id} | "
            f"provider={result.provider} | "
            f"routing={result.routing.value if result.routing else 'N/A'} | "
            f"confidence={result.confidence_score:.2f}"
        )

        store.save(result)
        return result

    except HTTPException as e:
        logger.error(f"HTTP Exception: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error no manejado: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando documento: {str(e)}",
        )


@app.get("/document/{document_id}", summary="Obtener resultado de procesamiento")
def get_document(document_id: str) -> DocumentResult:
    """Retorna el estado completo del documento procesado."""
    doc = store.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id!r} no encontrado")
    return doc


@app.post("/document/{document_id}/approve", summary="Aprobar y enviar a SAP")
def approve_document(document_id: str):
    """Envía el documento al SAP mock."""
    try:
        return store.approve(document_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/documents", summary="Listar documentos procesados")
def list_documents(limit: int = 20):
    """Lista los últimos N documentos procesados."""
    all_docs = store.all_documents()
    docs = all_docs[-limit:]
    return {
        "total": store.count(),
        "returned": len(docs),
        "documents": [
            {
                "document_id": d.document_id,
                "status": d.status,
                "provider": d.provider,
                "routing": d.routing,
                "confidence_score": d.confidence_score,
                "file_name": d.ingestion.file_name if d.ingestion else "",
                "uploaded_at": d.ingestion.uploaded_at if d.ingestion else "",
            }
            for d in reversed(docs)
        ],
    }


@app.get("/metrics", summary="Métricas del pipeline")
def get_metrics():
    """Estadísticas de procesamiento calculadas sobre los documentos en memoria."""
    docs = store.all_documents()

    if not docs:
        return {
            "total_documents": 0,
            "routing_distribution": {
                "AUTO_APPROVE": 0,
                "HITL_STANDARD": 0,
                "HITL_PRIORITY": 0,
                "AUTO_REJECT": 0,
            },
            "latency_p95_ms": 0,
            "agent_stats": [],
            "confidence_distribution": {
                "0-0.5": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
                "0.5-0.7": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
                "0.7-0.85": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
                "0.85-1.0": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
            },
        }

    # Routing distribution
    routing_dist = {"AUTO_APPROVE": 0, "HITL_STANDARD": 0, "HITL_PRIORITY": 0, "AUTO_REJECT": 0}
    for doc in docs:
        if doc.routing:
            key = doc.routing.value
            if key in routing_dist:
                routing_dist[key] += 1

    # Latency P95
    durations = [
        doc.processing_summary.total_duration_ms
        for doc in docs
        if doc.processing_summary
    ]
    latency_p95 = 0
    if durations:
        durations_sorted = sorted(durations)
        idx = max(0, int(len(durations_sorted) * 0.95) - 1)
        latency_p95 = durations_sorted[idx]

    # Agent stats
    agent_ids = ["agent_a", "agent_b", "agent_c"]
    agent_names = {"agent_a": "DocAI", "agent_b": "Tesseract", "agent_c": "Vertex"}
    agent_stats = []

    for agent_id in agent_ids:
        invocations = 0
        successes = 0
        timeouts = 0
        total_duration = 0
        confidences = []

        for doc in docs:
            output = doc.agent_outputs.get(agent_id)
            if output:
                invocations += 1
                if output.status.value == "SUCCESS":
                    successes += 1
                elif output.status.value == "TIMEOUT":
                    timeouts += 1
                total_duration += output.duration_ms
                field_confs = [f.confidence for f in output.fields.values() if f.confidence > 0]
                if field_confs:
                    confidences.append(sum(field_confs) / len(field_confs))

        if invocations > 0:
            agent_stats.append({
                "name": agent_names.get(agent_id, agent_id),
                "invocations": invocations,
                "successes": successes,
                "success_rate": successes / invocations,
                "timeout_rate": timeouts / invocations,
                "avg_duration_ms": total_duration / invocations,
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            })

    # Confidence distribution bucketed
    buckets: dict = {
        "0-0.5": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
        "0.5-0.7": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
        "0.7-0.85": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
        "0.85-1.0": {"agent_a": 0, "agent_b": 0, "agent_c": 0},
    }
    for doc in docs:
        for agent_id in agent_ids:
            output = doc.agent_outputs.get(agent_id)
            if output:
                for field in output.fields.values():
                    c = field.confidence
                    if c < 0.5:
                        buckets["0-0.5"][agent_id] += 1
                    elif c < 0.7:
                        buckets["0.5-0.7"][agent_id] += 1
                    elif c < 0.85:
                        buckets["0.7-0.85"][agent_id] += 1
                    else:
                        buckets["0.85-1.0"][agent_id] += 1

    return {
        "total_documents": len(docs),
        "routing_distribution": routing_dist,
        "latency_p95_ms": latency_p95,
        "agent_stats": agent_stats,
        "confidence_distribution": buckets,
    }


@app.delete("/documents/reset", summary="Limpiar todos los documentos (demo only)")
def reset_documents():
    """Limpia el estado en memoria. Solo para demos."""
    store.reset()
    from src.validation.generic import clear_duplicate_registry
    from src.sap.mock import clear_sap_registry
    clear_duplicate_registry()
    clear_sap_registry()
    return {"message": "Estado limpiado", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/providers", summary="Listar proveedores configurados")
def list_providers():
    from src.config.providers import get_all_providers
    providers = get_all_providers()
    return [
        {
            "provider_id": p.provider_id,
            "provider_name": p.provider_name,
            "category": p.category,
            "active": p.active,
        }
        for p in providers
    ]


@app.get("/document/{document_id}/pdf", summary="Descargar resultado en PDF")
def download_pdf(document_id: str):
    """Descarga un PDF con los datos extraídos formateado."""
    doc = _documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id!r} no encontrado")

    from src.pdf_generator import generate_result_pdf
    pdf_bytes = generate_result_pdf(doc)

    return JSONResponse(
        status_code=200,
        content={"data": __import__("base64").b64encode(pdf_bytes).decode()},
        headers={
            "Content-Disposition": f'attachment; filename="triunfo-{document_id[:8]}.pdf"'
        },
    )


@app.get("/logs", summary="Ver logs recientes")
def get_logs(limit: int = 50):
    """Retorna los últimos logs del sistema."""
    all_logs = get_memory_logs()
    return {
        "total": len(all_logs),
        "returned": min(limit, len(all_logs)),
        "logs": list(reversed(all_logs))[-limit:],
    }
