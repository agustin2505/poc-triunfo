# Triunfo — Spec-18 Prompts Multi-Fase para Extracción desde Imagen v1.0
# Version: 1.0
# Fecha: 2026-04-16
# Estado: Pendiente

## Objetivo
Definir los prompts de Fase 1 (imagen → JSON crudo) y Fase 2 (JSON crudo → payload SAP) que usan tanto el Agente Claude (Spec-19) como los Agentes Gemini (Specs 13-15). Adapta el patrón del archivo `REUSABLE_PROMPTS.md` al dominio de facturas argentinas con imagen como fuente de verdad.

Reemplaza los prompts de 2 pasos (imagen → texto libre → JSON) definidos en Spec-16 por un flujo directo imagen → JSON estructurado.

## Ubicación
`src/agents/prompts_imagen.py`  
Usado por: `src/agents/vertex/prompts.py` (Spec-16) y `src/agents/claude_vision.py` (Spec-19).

---

## Fase 1 — Extracción Visual Directa

### `SYSTEM_PROMPT_FASE1`

Candidato a prompt caching (Anthropic SDK). Incluir como bloque `system` con `cache_control: ephemeral`.

```
Sos un experto en procesamiento de facturas y comprobantes fiscales argentinos.

Tu tarea es EXTRAER datos de la imagen de factura con precisión absoluta.

REGLAS CRÍTICAS:
1. La imagen es la fuente de verdad. Si hay discrepancia entre texto y imagen, prevalece la imagen.
2. Extraé ÚNICAMENTE lo que está visible. Si un campo no se ve → null. NUNCA inventar.
3. Formato numérico: solo float/int, punto (.) para decimales, sin separadores de miles.
   Ejemplo: "1.234,56" → 1234.56
4. CUIT: extraer con guiones exactamente como aparece (XX-XXXXXXXX-X).
5. Fechas: formato ISO 8601 (YYYY-MM-DD). Si el año es de 2 dígitos, inferir el siglo.
6. Renglones: extraer TODOS los ítems del cuerpo de la factura, uno por uno.
7. Leé sellos, firmas, códigos de barras y QR si son visibles (texto, no decodificar).
8. NO clasificar el proveedor. NO calcular totales. NO completar campos faltantes.

Respondé ÚNICAMENTE con JSON válido, sin markdown, sin explicaciones.
```

### `USER_PROMPT_FASE1`
```
Extraé todos los datos de esta factura siguiendo el schema JSON exacto.
```

### Schema JSON Fase 1

```json
{
  "metadatos": {
    "tipo_comprobante": "FA/FB/FC/ND/NC/RE/...",
    "letra": "A/B/C/M/E",
    "punto_venta": null,
    "numero_comprobante": null,
    "fecha_emision": null,
    "fecha_vencimiento": null,
    "moneda": "ARS/USD",
    "cotizacion_tc": null,
    "cae": null,
    "vencimiento_cae": null,
    "codigo_barras_qr": null
  },
  "emisor": {
    "razon_social": null,
    "cuit": null,
    "domicilio": null,
    "condicion_iva": "RI/MO/EX/CF",
    "ingresos_brutos": null
  },
  "receptor": {
    "razon_social": null,
    "cuit": null,
    "domicilio": null,
    "condicion_iva": null
  },
  "renglones": [
    {
      "numero": 1,
      "descripcion": null,
      "cantidad": null,
      "unidad": null,
      "precio_unitario": null,
      "descuento_pct": null,
      "subtotal_sin_iva": null,
      "alicuota_iva": null,
      "monto_iva": null
    }
  ],
  "totales": {
    "subtotal_gravado": null,
    "subtotal_no_gravado": null,
    "subtotal_exento": null,
    "descuentos": null,
    "iva_105": null,
    "iva_21": null,
    "iva_27": null,
    "otros_impuestos": null,
    "percepciones_iibb": null,
    "percepciones_iva": null,
    "total": null
  },
  "datos_pago": {
    "condicion_pago": null,
    "vencimientos": [
      {"fecha": null, "monto": null}
    ]
  }
}
```

---

## Fase 2 — Mapeo a Schema SAP

### `SYSTEM_PROMPT_FASE2`

Candidato a prompt caching. Incluir como bloque `system` con `cache_control: ephemeral`.

```
Sos un experto en integración de comprobantes fiscales con SAP (módulo MM/FI, transacción MIRO).

Recibís un JSON de extracción (Fase 1) y debés mapearlo al schema SAP estándar de Triunfo.

REGLAS DE MAPEO:
- total → SAP BSEG-WRBTR
- fecha_emision → SAP BKPF-BLDAT
- fecha_vencimiento → SAP BSEG-ZFBDT
- numero completo = punto_venta (4 dígitos con ceros) + "-" + numero_comprobante (8 dígitos con ceros) → SAP BKPF-XBLNR
- emisor.cuit → lookup en maestro de proveedores (campo SAP LFA1-STCD1)
- moneda → SAP BKPF-WAERS
- monto_iva_total = iva_105 + iva_21 + iva_27 (nulos se tratan como 0)

REGLAS DE SIGNO:
- Factura (FA/FB/FC): total y montos como POSITIVOS
- Nota de Crédito (NC): total y montos como NEGATIVOS
- Nota de Débito (ND): total y montos como POSITIVOS

VALIDACIONES ANTES DE MAPEAR:
1. subtotal_gravado + subtotal_no_gravado + subtotal_exento ≈ suma previa a impuestos (tolerancia ±0.01)
2. base + iva_105 + iva_21 + iva_27 + otros_impuestos + percepciones ≈ total (tolerancia ±0.01)
3. Si validación falla → registrar en advertencias, no bloquear

Respondé ÚNICAMENTE con JSON válido, sin markdown, sin explicaciones.
```

### `USER_PROMPT_FASE2`
```
Mapeá el siguiente JSON al schema SAP:

{json_fase1}
```

### Schema JSON Fase 2 (output)

```json
{
  "sap_payload": {
    "lifnr": null,
    "bldat": null,
    "zfbdt": null,
    "wrbtr": null,
    "xblnr": null,
    "waers": "ARS",
    "bschl": null,
    "posiciones_iva": [
      {"mwskz": null, "hwste": null}
    ]
  },
  "trazabilidad": {
    "campos_mapeados": 0,
    "campos_con_null": 0,
    "validacion_matematica_ok": true,
    "advertencias": []
  }
}
```

---

## Reglas de construcción de prompts

### `build_fase1_messages(image_base64, mime_type) -> list`
- Para Claude: lista de mensajes con `role: user`, content incluyendo bloque `image` (base64) + bloque `text` con `USER_PROMPT_FASE1`
- Para Gemini: lista de `Part` con `Part.from_data(image_bytes, mime_type)` + `Part.from_text(USER_PROMPT_FASE1)`

### `build_fase2_messages(json_fase1_str) -> list`
- Para Claude: lista de mensajes con `role: user`, content incluyendo `USER_PROMPT_FASE2` con `{json_fase1}` interpolado
- Para Gemini: lista de `Part` con el texto del prompt interpolado

### `inject_schema(prompt, schema_dict) -> str`
- Utilidad que adjunta el schema JSON al final del system prompt como referencia de estructura esperada

---

## Criterio de aceptación

- [ ] `SYSTEM_PROMPT_FASE1` y `USER_PROMPT_FASE1` definidos como constantes en `prompts_imagen.py`
- [ ] `SYSTEM_PROMPT_FASE2` y `USER_PROMPT_FASE2` definidos como constantes en `prompts_imagen.py`
- [ ] `SCHEMA_FASE1` y `SCHEMA_FASE2` definidos como dict (para validar estructura del output)
- [ ] `build_fase1_messages(image_base64, mime_type)` retorna formato correcto para Claude
- [ ] `build_fase1_messages_gemini(image_bytes, mime_type)` retorna lista de `Part` para Gemini
- [ ] `build_fase2_messages(json_fase1_str)` retorna lista de mensajes para Claude y Gemini
- [ ] Spec-16 `prompts.py` importa desde `prompts_imagen.py` (no duplicar contenido)
- [ ] Test: `build_fase1_messages` genera bloque de imagen válido con base64 correcto
- [ ] Test: `build_fase2_messages` interpola el JSON en el prompt sin errores de encoding

## Dependencias
- Spec-03 (schema de campos del AgentOutput — los campos de Fase 1 se mapean a los campos estándar)
- Spec-13, 14, 15 (consumen `build_fase1_messages_gemini`)
- Spec-19 (consume `build_fase1_messages` para Claude)

## Out of scope
- Few-shot examples por proveedor (Edenor, Metrogas): quedan para iteración posterior de prompts
- Validación semántica de campos (ej: CUIT válido por dígito verificador): incumbe a Spec-05
