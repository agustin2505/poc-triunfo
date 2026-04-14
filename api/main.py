"""API FastAPI para el MVP Triunfo."""
from __future__ import annotations

import uuid
import traceback
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.models.document import DocumentResult, RoutingDecision
from src.pipeline.processor import Pipeline
from src.sap.mock import post_to_sap
from src.logging_setup import setup_logging, get_memory_logs

logger = setup_logging("triunfo.api")

app = FastAPI(
    title="Triunfo — MVP OCR/IDP",
    description="Pipeline de extracción de facturas con 5 agentes y conciliación por mayoría",
    version="1.0.0",
)

logger.info("=== Triunfo API iniciando ===")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir frontend estático
import os
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# Storage en memoria para el MVP
_documents: Dict[str, DocumentResult] = {}
_pipeline = Pipeline()


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
        )

        logger.info(
            f"Pipeline completado: {result.document_id} | "
            f"provider={result.provider} | "
            f"routing={result.routing.value if result.routing else 'N/A'} | "
            f"confidence={result.confidence_score:.2f}"
        )

        _documents[result.document_id] = result
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
    doc = _documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id!r} no encontrado")
    return doc


@app.post("/document/{document_id}/approve", summary="Aprobar y enviar a SAP")
def approve_document(document_id: str):
    """
    Envía el documento al SAP mock.
    Solo disponible para documentos con routing AUTO_APPROVE o HITL_STANDARD aprobado.
    """
    doc = _documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Documento {document_id!r} no encontrado")

    if doc.routing == RoutingDecision.AUTO_REJECT:
        raise HTTPException(
            status_code=422,
            detail="El documento fue rechazado automáticamente y no puede enviarse a SAP",
        )

    # Obtener campos necesarios para SAP
    fields = doc.extracted_fields
    ref = (fields.get("reference_number") or type("", (), {"value": None})()).value
    total = (fields.get("total_amount") or type("", (), {"value": 0})()).value
    currency = (fields.get("currency") or type("", (), {"value": "ARS"})()).value
    issue_date = (fields.get("issue_date") or type("", (), {"value": ""})()).value

    request_id = str(uuid.uuid4())
    from src.config.sede import get_sede
    sede = get_sede(doc.ingestion.sede_id if doc.ingestion else "demo-001")
    sap_company = sede.sap_company_code if sede else "AR00"

    sap_response = post_to_sap(
        request_id=request_id,
        document_id=document_id,
        sede_id=doc.ingestion.sede_id if doc.ingestion else "demo-001",
        provider=doc.provider or "",
        provider_id=doc.provider_id or "",
        reference_number=str(ref) if ref else f"REF-{document_id[:8]}",
        total_amount=float(total) if total else 0.0,
        currency=str(currency) if currency else "ARS",
        issue_date=str(issue_date) if issue_date else "",
        sap_company_code=sap_company,
        extracted_fields={k: v.model_dump() for k, v in fields.items()},
    )

    doc.sap_response = sap_response
    _documents[document_id] = doc
    return sap_response


@app.get("/documents", summary="Listar documentos procesados")
def list_documents(limit: int = 20):
    """Lista los últimos N documentos procesados."""
    docs = list(_documents.values())[-limit:]
    return {
        "total": len(_documents),
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


@app.delete("/documents/reset", summary="Limpiar todos los documentos (demo only)")
def reset_documents():
    """Limpia el estado en memoria. Solo para demos."""
    _documents.clear()
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
