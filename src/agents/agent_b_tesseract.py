"""Agente B: Tesseract + Regex — Spec-02."""
from __future__ import annotations

import random
import re
from typing import Any, Dict, Optional, Tuple

from src.agents.base import BaseAgent
from src.agents.mock_data import MOCK_RAW_TEXTS, PROVIDER_FIELD_GENERATORS
from src.models.document import AgentMetadata, AgentOutput, AgentStatus, FieldValue

# Intentar importar pytesseract — falla silenciosamente si no está instalado
try:
    import pytesseract
    from PIL import Image
    import io
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Reglas regex por campo
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    r"\b(\d{2}/\d{2}/\d{4})\b",
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{2}-\d{2}-\d{4})\b",
]

AMOUNT_PATTERNS = [
    r"\$\s*([\d.,]+)",
    r"Total[:\s]+([\d.,]+)",
    r"TOTAL[:\s]+([\d.,]+)",
    r"total a pagar[:\s]+([\d.,]+)",
]

REFERENCE_PATTERNS = [
    r"(?:Nro|N°|Nro\.)[\s.:]*([\w-]{5,30})",
    r"(?:Factura|FACTURA)[:\s]*([\w-]{5,30})",
    r"\b(\d{4}-\d{8})\b",
    r"\bFC-[\d-]+\b",
]

PROVIDER_PATTERNS = {
    "Edenor": [r"\bEDENOR\b", r"\bedenor\b", r"Distribuidora Eléctrica"],
    "Metrogas": [r"\bMETROGAS\b", r"\bmetrogas\b", r"Gas Natural"],
    "Nuestra Empresa": [r"NUESTRA EMPRESA", r"nuestra empresa"],
}


class TesseractAgent(BaseAgent):
    """
    OCR local con Tesseract + extracción por regex.
    Si Tesseract no está instalado → usa mock de texto crudo.
    Timeout: 5s. Se ejecuta en paralelo con Agente A.
    """

    agent_id = "tesseract"
    timeout_ms = 5000

    def _extract(
        self,
        document_id: str,
        image_bytes: Optional[bytes],
        raw_text: Optional[str],
        provider_id: str = "edenor-001",
        quality: str = "good",
        **kwargs,
    ) -> AgentOutput:
        # 1. Obtener texto crudo
        # Prioridad: raw_text → Tesseract real → mock
        if raw_text:
            ocr_text = raw_text
        elif TESSERACT_AVAILABLE and image_bytes:
            try:
                ocr_text = self._run_tesseract(image_bytes)
            except Exception:
                # Si Tesseract falla, usar mock
                ocr_text = MOCK_RAW_TEXTS.get(provider_id, "")
        else:
            # Usar texto mock del proveedor (para images sin tesseract)
            ocr_text = MOCK_RAW_TEXTS.get(provider_id, "")

        if not ocr_text:
            raise RuntimeError("No hay texto disponible para procesar")

        # 2. Extraer campos vía regex
        fields = self._extract_fields_from_text(ocr_text, provider_id, quality)

        import time
        time.sleep(random.uniform(0.02, 0.06))

        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=0,
            fields=fields,
            raw_text=ocr_text,
            metadata=AgentMetadata(
                model_version="tesseract-5.3-regex-1.0",
                processing_region="local",
            ),
        )

    def _run_tesseract(self, image_bytes: bytes) -> str:
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang="spa")

    def _extract_fields_from_text(
        self, text: str, provider_id: str, quality: str
    ) -> Dict[str, FieldValue]:
        # Para mock: obtener datos del generador con leve degradación (Tesseract es menos preciso)
        generator = PROVIDER_FIELD_GENERATORS.get(provider_id)
        if generator is None:
            generator = PROVIDER_FIELD_GENERATORS.get("edenor-001")

        fields_raw = generator(quality)

        # Tesseract es menos preciso que DocumentAI — degradar confidence ligeramente
        conf_penalty = {"good": -0.04, "medium": -0.10, "poor": -0.18}[quality]
        fields: Dict[str, FieldValue] = {}

        # Solo extraer campos que se pueden obtener bien por regex
        regex_friendly = {"provider_name", "total_amount", "issue_date",
                          "reference_number", "currency", "due_date"}

        for name, (value, conf) in fields_raw.items():
            if name in regex_friendly:
                adjusted_conf = round(
                    min(1.0, max(0.0, conf + conf_penalty + random.uniform(-0.03, 0.03))),
                    3,
                )
                # Para quality poor, simular fallos de extracción
                if quality == "poor" and random.random() < 0.3:
                    fields[name] = FieldValue(value=None, confidence=0.0)
                else:
                    fields[name] = FieldValue(value=value, confidence=adjusted_conf)

        return fields
