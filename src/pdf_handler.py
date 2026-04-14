"""Manejador de PDFs — extrae texto de PDFs seleccionables o escaneados."""
from __future__ import annotations

import io
from typing import Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def extract_from_pdf(pdf_bytes: bytes) -> Tuple[str, list[bytes]]:
    """
    Extrae texto de un PDF (seleccionable o escaneado).

    Retorna:
    - (texto extraído, lista de imágenes de páginas)

    Si el PDF tiene texto seleccionable, lo extrae directamente.
    Si es escaneado, intenta OCR con Tesseract (si disponible) o retorna mock.
    """
    if not PDFPLUMBER_AVAILABLE:
        return "PDF no procesado (pdfplumber no instalado)", []

    try:
        pdf_file = io.BytesIO(pdf_bytes)
        all_text = []
        page_images = []

        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Intenta extraer texto directo (PDF con texto seleccionable)
                text = page.extract_text() or ""

                if not text.strip():
                    # Si no hay texto, es escaneado → intenta OCR
                    if TESSERACT_AVAILABLE:
                        # Renderizar página a imagen
                        from pdf2image import convert_from_bytes
                        images = convert_from_bytes(pdf_bytes, first_page=page_num+1, last_page=page_num+1)
                        if images:
                            img = images[0]
                            text = pytesseract.image_to_string(img, lang="spa")
                            # Guardar imagen de la página
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format="JPEG")
                            page_images.append(img_bytes.getvalue())
                    else:
                        text = f"[Página {page_num+1} escaneada — Tesseract no disponible]"

                all_text.append(f"--- Página {page_num+1} ---\n{text}")

        return "\n\n".join(all_text), page_images

    except Exception as e:
        return f"Error al procesar PDF: {e}", []


def convert_pdf_page_to_image(pdf_bytes: bytes, page_num: int = 0) -> bytes:
    """
    Convierte una página de PDF a imagen JPEG.
    Usado para preview en UI.
    """
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, first_page=page_num+1, last_page=page_num+1)
        if images:
            img_bytes = io.BytesIO()
            images[0].save(img_bytes, format="JPEG")
            return img_bytes.getvalue()
    except ImportError:
        pass
    except Exception:
        pass

    return b""
