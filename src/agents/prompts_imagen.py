"""Prompts multi-fase para extracción de facturas desde imagen — Spec-18.

Patrón: Fase 1 (imagen → JSON crudo) + Fase 2 (JSON crudo → payload SAP).
Compartido por ClaudeVisionAgent y los agentes Gemini de Vertex AI.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.models.document import AgentOutput, FieldValue

# ---------------------------------------------------------------------------
# Fase 1 — System prompt (candidato a prompt caching en Anthropic SDK)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_FASE1 = """Sos un experto en procesamiento de facturas y comprobantes fiscales argentinos.

Tu tarea es EXTRAER datos de la imagen de factura con precision absoluta.

REGLAS CRITICAS:
1. La imagen es la fuente de verdad. Si hay discrepancia entre texto y imagen, prevalece la imagen.
2. Extrae UNICAMENTE lo que esta visible. Si un campo no se ve -> null. NUNCA inventar.
3. Formato numerico: solo float/int, punto (.) para decimales, sin separadores de miles.
   Ejemplo: "1.234,56" -> 1234.56
4. CUIT: extraer con guiones exactamente como aparece (XX-XXXXXXXX-X).
5. Fechas: formato ISO 8601 (YYYY-MM-DD). Si el anio es de 2 digitos, inferir el siglo.
6. Renglones: extraer TODOS los items del cuerpo de la factura, uno por uno.
7. Lee sellos, firmas, codigos de barras y QR si son visibles (texto, no decodificar).
8. NO clasificar el proveedor. NO calcular totales. NO completar campos faltantes.
9. NIC (Numero de Identificacion del Cliente): campo prominente en facturas de servicios publicos (luz, gas, agua). Extraer en metadatos.nic.
10. impuestos_tasas: extraer TODOS los impuestos, tasas y contribuciones como lista. Cada item tiene descripcion (nombre del tributo) y monto. Incluir FNEE, contribuciones provinciales, municipales, tasas municipales, etc.
11. EMISOR vs RECEPTOR — regla fundamental:
    - emisor: la empresa/entidad que EMITE la factura. Su nombre, CUIT y domicilio fiscal aparecen en el encabezado o membrete (ej: la distribuidora electrica, la empresa de gas, el proveedor comercial). Es SIEMPRE una empresa o entidad, nunca una persona fisica titular del servicio.
    - receptor: la persona o empresa que RECIBE la factura. En facturas de servicios publicos aparece como "Titular", "Cliente", "Datos del cliente" o "A nombre de". Su nombre puede ser una persona fisica (ej: PEREZ VICTORIA).
    - razon_social es siempre un NOMBRE (de persona o empresa). NUNCA una direccion ni un numero de calle.
    - domicilio es siempre una DIRECCION (calle, numero, ciudad). NUNCA un nombre de persona.
    - Si ves un campo con formato "APELLIDO NOMBRE" o "NOMBRE APELLIDO" -> es razon_social.
    - Si ves un campo con formato "CALLE NUMERO CIUDAD" -> es domicilio.

Responde UNICAMENTE con JSON valido, sin markdown, sin explicaciones."""

USER_PROMPT_FASE1 = "Extrae todos los datos de esta factura siguiendo el schema JSON exacto."

# ---------------------------------------------------------------------------
# Fase 2 — System prompt (candidato a prompt caching en Anthropic SDK)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_FASE2 = """Sos un experto en integracion de comprobantes fiscales con SAP (modulo MM/FI, transaccion MIRO).

Recibis un JSON de extraccion (Fase 1) y debes mapearlo al schema SAP estandar de Triunfo.

REGLAS DE MAPEO:
- totales.total -> SAP BSEG-WRBTR
- metadatos.fecha_emision -> SAP BKPF-BLDAT
- metadatos.fecha_vencimiento -> SAP BSEG-ZFBDT
- numero completo = punto_venta (4 digitos con ceros) + "-" + numero_comprobante (8 digitos con ceros) -> SAP BKPF-XBLNR
- emisor.cuit -> lookup maestro de proveedores SAP (LFA1-STCD1)
- metadatos.moneda -> SAP BKPF-WAERS
- monto_iva_total = iva_105 + iva_21 + iva_27 (nulos se tratan como 0)

REGLAS DE SIGNO:
- Factura (FA/FB/FC): total y montos como POSITIVOS
- Nota de Credito (NC): total y montos como NEGATIVOS
- Nota de Debito (ND): total y montos como POSITIVOS

VALIDACIONES ANTES DE MAPEAR:
1. subtotal_gravado + subtotal_no_gravado + subtotal_exento aprox igual a suma previa a impuestos (tolerancia 0.01)
2. base + iva_105 + iva_21 + iva_27 + otros_impuestos + percepciones aprox igual a total (tolerancia 0.01)
3. Si validacion falla -> registrar en advertencias, no bloquear

Responde UNICAMENTE con JSON valido, sin markdown, sin explicaciones."""

USER_PROMPT_FASE2 = "Mapea el siguiente JSON al schema SAP:\n\n{json_fase1}"

# ---------------------------------------------------------------------------
# Schemas de referencia (para inject_schema y validación de estructura)
# ---------------------------------------------------------------------------

SCHEMA_FASE1: Dict[str, Any] = {
    "metadatos": {
        "tipo_comprobante": None,
        "letra": None,
        "punto_venta": None,
        "numero_comprobante": None,
        "fecha_emision": None,
        "fecha_vencimiento": None,
        "moneda": "ARS",
        "cotizacion_tc": None,
        "cae": None,
        "vencimiento_cae": None,
        "codigo_barras_qr": None,
        "nic": None,
    },
    "emisor": {
        "razon_social": None,
        "cuit": None,
        "domicilio": None,
        "condicion_iva": None,
        "ingresos_brutos": None,
    },
    "receptor": {
        "razon_social": None,
        "cuit": None,
        "domicilio": None,
        "condicion_iva": None,
    },
    "renglones": [
        {
            "numero": 1,
            "descripcion": None,
            "cantidad": None,
            "unidad": None,
            "precio_unitario": None,
            "descuento_pct": None,
            "subtotal_sin_iva": None,
            "alicuota_iva": None,
            "monto_iva": None,
        }
    ],
    "impuestos_tasas": [
        {
            "descripcion": None,
            "monto": None,
        }
    ],
    "totales": {
        "subtotal_gravado": None,
        "subtotal_no_gravado": None,
        "subtotal_exento": None,
        "descuentos": None,
        "iva_105": None,
        "iva_21": None,
        "iva_27": None,
        "otros_impuestos": None,
        "percepciones_iibb": None,
        "percepciones_iva": None,
        "total": None,
    },
    "datos_pago": {
        "condicion_pago": None,
        "vencimientos": [{"fecha": None, "monto": None}],
    },
}

SCHEMA_FASE2: Dict[str, Any] = {
    "sap_payload": {
        "lifnr": None,
        "bldat": None,
        "zfbdt": None,
        "wrbtr": None,
        "xblnr": None,
        "waers": "ARS",
        "bschl": None,
        "posiciones_iva": [{"mwskz": None, "hwste": None}],
    },
    "trazabilidad": {
        "campos_mapeados": 0,
        "campos_con_null": 0,
        "validacion_matematica_ok": True,
        "advertencias": [],
    },
}

# ---------------------------------------------------------------------------
# Builders de mensajes — Claude (Anthropic)
# ---------------------------------------------------------------------------

def build_fase1_messages_claude(image_base64: str, mime_type: str = "image/jpeg") -> List[Dict]:
    """Construye el array de mensajes para la API de Anthropic (Fase 1)."""
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": USER_PROMPT_FASE1,
                },
            ],
        }
    ]


def build_fase2_messages_claude(json_fase1_str: str) -> List[Dict]:
    """Construye el array de mensajes para la API de Anthropic (Fase 2)."""
    return [
        {
            "role": "user",
            "content": USER_PROMPT_FASE2.format(json_fase1=json_fase1_str),
        }
    ]


# ---------------------------------------------------------------------------
# Builders de mensajes — Gemini (Vertex AI)
# ---------------------------------------------------------------------------

def build_fase1_parts_gemini(image_bytes: bytes, mime_type: str = "image/jpeg") -> List:
    """Construye la lista de Part para la API de Vertex AI (Fase 1).

    Returns lista de Part con imagen + prompt de usuario.
    Requiere: from vertexai.generative_models import Part
    """
    try:
        from vertexai.generative_models import Part
    except ImportError:
        raise ImportError(
            "google-cloud-aiplatform no está instalado. "
            "Ejecutar: pip install google-cloud-aiplatform"
        )
    system_with_schema = inject_schema(
        SYSTEM_PROMPT_FASE1 + "\n\nSchema esperado:\n",
        SCHEMA_FASE1,
    )
    return [
        Part.from_data(data=image_bytes, mime_type=mime_type),
        Part.from_text(system_with_schema + "\n\n" + USER_PROMPT_FASE1),
    ]


def build_fase2_parts_gemini(json_fase1_str: str) -> List:
    """Construye la lista de Part para la API de Vertex AI (Fase 2)."""
    try:
        from vertexai.generative_models import Part
    except ImportError:
        raise ImportError(
            "google-cloud-aiplatform no está instalado. "
            "Ejecutar: pip install google-cloud-aiplatform"
        )
    prompt = (
        SYSTEM_PROMPT_FASE2
        + "\n\nSchema esperado:\n"
        + json.dumps(SCHEMA_FASE2, indent=2, ensure_ascii=False)
        + "\n\n"
        + USER_PROMPT_FASE2.format(json_fase1=json_fase1_str)
    )
    return [Part.from_text(prompt)]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def inject_schema(prompt: str, schema_dict: Dict) -> str:
    """Adjunta el schema JSON al final del prompt."""
    return prompt + json.dumps(schema_dict, indent=2, ensure_ascii=False)


def parse_json_response(text: str) -> Dict:
    """Parsea el texto del modelo eliminando posibles bloques markdown."""
    text = text.strip()
    # Eliminar bloques ```json ... ``` si los hay
    if text.startswith("```"):
        lines = text.splitlines()
        # Sacar primera línea (```json o ```) y última línea (```)
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return json.loads(text)


def map_fase1_to_agent_fields(fase1: Dict) -> Dict[str, FieldValue]:
    """Mapea el JSON de Fase 1 a los campos estándar del AgentOutput (Spec-03).

    Los campos estándar son los que espera el Conciliador:
    provider_name, customer_name, nic, issue_date, due_date, total_amount,
    reference_number, currency, supplier_cuit, invoice_type, net_amount,
    tax_amount, impuestos_tasas, cae, cae_due_date.
    """
    meta = fase1.get("metadatos") or {}
    emisor = fase1.get("emisor") or {}
    receptor = fase1.get("receptor") or {}
    totales = fase1.get("totales") or {}
    impuestos_raw = fase1.get("impuestos_tasas") or []

    def fv(value: Any, conf: float = 0.90) -> FieldValue:
        if value is None or value == "":
            return FieldValue(value=None, confidence=0.0)
        return FieldValue(value=value, confidence=conf)

    # Número de comprobante completo
    pv = meta.get("punto_venta")
    nc = meta.get("numero_comprobante")
    if pv and nc:
        ref = f"{str(pv).zfill(4)}-{str(nc).zfill(8)}"
    elif nc:
        ref = str(nc)
    elif pv:
        ref = str(pv)
    else:
        ref = None

    # Tipo de comprobante (ej: "FB", "FA", "NC")
    tipo = meta.get("tipo_comprobante") or ""
    letra = meta.get("letra") or ""
    invoice_type = (tipo + letra).strip() or None

    # IVA total
    iva_vals = [
        totales.get("iva_105"),
        totales.get("iva_21"),
        totales.get("iva_27"),
    ]
    iva_sum = sum(v for v in iva_vals if v is not None)
    tax_amount: Optional[float] = iva_sum if iva_sum > 0 else None

    # Impuestos, tasas y contribuciones como lista filtrada
    impuestos_lista = [
        item for item in impuestos_raw
        if isinstance(item, dict)
        and item.get("descripcion") is not None
        and item.get("monto") is not None
    ]

    return {
        "provider_name": fv(emisor.get("razon_social"), 0.92),
        "customer_name": fv(receptor.get("razon_social"), 0.90),
        "customer_address": fv(receptor.get("domicilio"), 0.88),
        "nic": fv(meta.get("nic"), 0.93),
        "issue_date": fv(meta.get("fecha_emision"), 0.93),
        "due_date": fv(meta.get("fecha_vencimiento"), 0.88),
        "total_amount": fv(totales.get("total"), 0.94),
        "reference_number": fv(ref, 0.90),
        "currency": fv(meta.get("moneda") or "ARS", 0.97),
        "supplier_cuit": fv(emisor.get("cuit"), 0.91),
        "invoice_type": fv(invoice_type, 0.88),
        "net_amount": fv(totales.get("subtotal_gravado"), 0.89),
        "tax_amount": fv(tax_amount, 0.89),
        "impuestos_tasas": fv(impuestos_lista if impuestos_lista else None, 0.88),
        "cae": fv(meta.get("cae"), 0.86),
        "cae_due_date": fv(meta.get("vencimiento_cae"), 0.85),
    }
