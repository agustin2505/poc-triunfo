"""Generador de PDF con resultados de extracción."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    Image as RLImage
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.models.document import DocumentResult


def generate_result_pdf(result: DocumentResult) -> bytes:
    """
    Genera un PDF con los resultados de la extracción formateado profesionalmente.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderColor=colors.HexColor('#d1d5db'),
        borderWidth=0.5,
        borderPadding=4,
    )

    story = []

    # Header
    story.append(Paragraph("Triunfo — Reporte de Extracción", title_style))
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    story.append(Paragraph(f"<font size=9 color='#6b7280'>Generado: {timestamp}</font>", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Info del documento
    story.append(Paragraph("Información del Documento", heading_style))
    info_data = [
        ["Campo", "Valor"],
        ["ID Documento", result.document_id[:12] + "..."],
        ["Estado", result.status.value if result.status else "—"],
        ["Proveedor", result.provider or "—"],
        ["Categoría", result.category.value if result.category else "—"],
        ["Confidence Global", f"{(result.confidence_score or 0) * 100:.1f}%"],
        ["Routing", result.routing.value if result.routing else "—"],
    ]
    info_table = Table(info_data, colWidths=[2.0*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))

    # Datos extraídos
    story.append(Paragraph("Datos Extraídos", heading_style))
    extracted = result.extracted_fields or {}
    if extracted:
        data = [["Campo", "Valor", "Confidence", "Fuente"]]
        for fname, cf in sorted(extracted.items()):
            val_str = str(cf.value)[:40] if cf.value else "—"
            conf_str = f"{(cf.confidence or 0) * 100:.0f}%"
            source_str = cf.source or "—"
            data.append([fname, val_str, conf_str, source_str])

        table = Table(data, colWidths=[1.5*inch, 2.0*inch, 1.0*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (2, 0), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("<font color='#ef4444'>Sin datos extraídos</font>", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Validaciones
    if result.validation:
        story.append(Paragraph("Validaciones", heading_style))
        val = result.validation
        status_color = '#22c55e' if val.is_consistent else '#ef4444'
        status_text = "✓ PASADAS" if val.is_consistent else "✗ FALLIDAS"
        story.append(Paragraph(f"<font color='{status_color}' size=10><b>{status_text}</b></font>", styles['Normal']))

        if val.errors:
            story.append(Paragraph("<font size=9><b>Errores:</b></font>", styles['Normal']))
            for err in val.errors:
                story.append(Paragraph(f"• {err}", styles['Normal']))

        if val.warnings:
            story.append(Paragraph("<font size=9><b>Advertencias:</b></font>", styles['Normal']))
            for warn in val.warnings:
                story.append(Paragraph(f"• {warn}", styles['Normal']))

        story.append(Spacer(1, 0.15*inch))

    # Metrics
    if result.processing_summary:
        story.append(Paragraph("Métricas de Procesamiento", heading_style))
        summary = result.processing_summary
        metrics_data = [
            ["Métrica", "Valor"],
            ["Duración total", f"{(summary.total_duration_ms or 0) / 1000:.2f}s"],
            ["Modelos usados", ", ".join(summary.models_used) or "—"],
            ["Campos faltantes", ", ".join(summary.missing_fields[:3]) or "Ninguno"],
        ]
        metrics_table = Table(metrics_data, colWidths=[2.0*inch, 3.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.2*inch))

    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_text = f"Triunfo MVP | {result.document_id[:8]}"
    story.append(Paragraph(
        f"<font size=7 color='#9ca3af'>{footer_text}</font>",
        ParagraphStyle('footer', parent=styles['Normal'], alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
