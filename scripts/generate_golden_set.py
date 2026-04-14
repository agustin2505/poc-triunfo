#!/usr/bin/env python3
"""
Genera el golden set de 30 documentos de prueba — Spec-10.

Crea imágenes sintéticas de facturas para los 3 proveedores con variabilidad
de calidad y produce golden-set-manifest.json.

Uso:
    python scripts/generate_golden_set.py --output docs/specs-mvp/golden-set-manifest.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List

# Agregar raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARN: Pillow no instalado. Las imágenes serán placeholders de 1px.", file=sys.stderr)

from src.agents.mock_data import (
    edenor_fields, factura_interna_fields, metrogas_fields
)


PROVIDERS = [
    ("edenor", "edenor-001", "Edenor", "SERVICIOS", edenor_fields),
    ("metrogas", "metrogas-001", "Metrogas", "SERVICIOS", metrogas_fields),
    ("factura_interna", "factura-interna-001", "Nuestra Empresa", "FACTURA_NEGOCIO", factura_interna_fields),
]

QUALITY_DIST = ["good"] * 8 + ["medium", "poor"]  # 80% good, 10% medium, 10% poor


def generate_invoice_image(provider: str, quality: str, fields: dict) -> bytes:
    """Genera una imagen sintética de factura."""
    if not PIL_AVAILABLE:
        return b"\x89PNG\r\n\x1a\n"  # PNG mínimo válido de 1px

    # Crear imagen base
    width, height = 800, 1100
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Header del proveedor
    draw.rectangle([(0, 0), (width, 120)], fill=(30, 60, 120))
    draw.text((40, 30), provider.upper(), fill=(255, 255, 255))
    draw.text((40, 70), "FACTURA DE SERVICIOS", fill=(200, 220, 255))

    # Campos
    y = 150
    font_size = 16
    for field_name, (value, conf) in fields.items():
        if value is None:
            continue
        label = field_name.replace("_", " ").upper()
        val_str = str(value)[:40]
        draw.text((40, y), f"{label}:", fill=(80, 80, 80))
        draw.text((250, y), val_str, fill=(0, 0, 0))
        y += 30
        if y > height - 100:
            break

    draw.line([(40, height - 80), (width - 40, height - 80)], fill=(200, 200, 200), width=1)
    draw.text((40, height - 60), "Documento generado por Triunfo MVP", fill=(150, 150, 150))

    # Aplicar degradación de calidad
    if quality == "medium":
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        # Agregar ruido ligero
        import random
        for _ in range(5000):
            x = random.randint(0, width - 1)
            y_pos = random.randint(0, height - 1)
            gray = random.randint(180, 240)
            img.putpixel((x, y_pos), (gray, gray, gray))
    elif quality == "poor":
        # Rotación + blur fuerte + bajo contraste
        img = img.rotate(random.uniform(-8, 8), expand=True, fillcolor=(240, 240, 240))
        img = img.filter(ImageFilter.GaussianBlur(radius=2.5))
        from PIL import ImageEnhance
        img = ImageEnhance.Contrast(img).enhance(0.6)

    # Convertir a bytes
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85 if quality == "good" else 70)
    return buf.getvalue()


def build_expected_fields(fields_raw: dict) -> dict:
    """Construye expected_fields para el manifesto."""
    expected = {}
    for fname, (value, _conf) in fields_raw.items():
        if value is not None and fname != "line_items":
            expected[fname] = value
    return expected


def main():
    import random
    parser = argparse.ArgumentParser(description="Genera golden set de 30 documentos")
    parser.add_argument("--output", default="docs/specs-mvp/golden-set-manifest.json",
                        help="Ruta del manifesto de salida")
    parser.add_argument("--images-dir", default="data/golden-set",
                        help="Directorio donde guardar las imágenes")
    args = parser.parse_args()

    os.makedirs(args.images_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    manifest: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": 30,
        "distribution": "10 per provider × 3 providers",
        "quality_dist": "8 good + 1 medium + 1 poor per provider",
        "golden_set": [],
    }

    total = 0
    for slug, provider_id, provider_name, category, field_gen in PROVIDERS:
        for i, quality in enumerate(QUALITY_DIST):
            doc_id = f"{slug}-{i:03d}-{uuid.uuid4().hex[:8]}"
            fields_raw = field_gen(quality)
            expected = build_expected_fields(fields_raw)

            # Generar imagen
            img_bytes = generate_invoice_image(provider_name, quality, fields_raw)
            img_path = os.path.join(args.images_dir, slug, f"{doc_id}.jpg")
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with open(img_path, "wb") as f:
                f.write(img_bytes)

            manifest["golden_set"].append({
                "document_id": doc_id,
                "provider": provider_name,
                "provider_id": provider_id,
                "category": category,
                "quality": quality,
                "expected_fields": expected,
                "local_path": img_path,
                "gcs_uri": f"gs://triunfo-demo/golden-set/{slug}/{doc_id}.jpg",
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "ground_truth_confidence_min": {
                    "good": 0.88,
                    "medium": 0.70,
                    "poor": 0.50,
                }[quality],
            })
            total += 1

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    print(f"✓ Golden set generado: {total} documentos")
    print(f"  Imágenes: {args.images_dir}/")
    print(f"  Manifesto: {args.output}")


if __name__ == "__main__":
    import random
    main()
