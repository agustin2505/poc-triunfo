# Triunfo — Estrategia de Precisión: Target >95% en Extracción de Facturas

> **Principio rector**: En datos de facturación, un falso positivo (campo incorrecto aceptado como correcto) es más dañino que un falso negativo (campo correcto enviado a revisión humana). El sistema debe priorizar **no dejar pasar errores** por sobre maximizar throughput automático.

---

## 1. Modelo de precisión por capas

La precisión final no depende de un solo componente. Es el resultado acumulativo de **7 capas defensivas**, cada una diseñada para atrapar lo que la anterior dejó pasar.

```
Capa 1: Captura guiada           ──► elimina basura antes de entrar
Capa 2: Preprocesamiento         ──► maximiza legibilidad para el OCR
Capa 3: OCR/IDP primario         ──► extracción base (Document AI)
Capa 4: Post-procesamiento ML    ──► corrige y enriquece con modelo AR
Capa 5: Validaciones cruzadas    ──► detecta inconsistencias numéricas/fiscales
Capa 6: Confidence scoring       ──► clasifica certeza y rutea a HITL
Capa 7: HITL + feedback loop     ──► corrección humana + reentrenamiento
```

**Target combinado**: si cada capa mejora la precisión incremental, el sistema alcanza >95% sin HITL y >99% con HITL.

| Escenario | Target accuracy campos obligatorios |
|---|---|
| Imagen buena calidad, sin HITL | > 97% |
| Imagen baja calidad, sin HITL | > 92% |
| **Cualquier imagen, con HITL** | **> 99%** |
| **Promedio ponderado operativo** | **> 95%** |

---

## 2. Capa 1 — Captura guiada (prevención en origen)

**Problema**: la mayoría de los errores de OCR nacen en una mala foto, no en un mal modelo.

### Controles en el cliente mobile/web

| Control | Implementación | Impacto en precisión |
|---|---|---|
| **Detección de bordes en tiempo real** | OpenCV en el dispositivo (JS/WASM o nativo). Overlay que muestra el área detectada de la factura y no permite disparar la foto hasta que encuadre correctamente | Elimina fotos cortadas, rotadas 90°, o con fondo excesivo |
| **Detección de blur en tiempo real** | Variance of Laplacian. Si el score < umbral, mostrar aviso "imagen borrosa, volvé a intentar" | Evita que entren fotos irrecuperables |
| **Detección de iluminación** | Histograma de luminosidad. Si >40% de píxeles saturados (blancos o negros), advertir | Reduce fotos con flash directo, sombras, o subexposición |
| **Resolución mínima** | Rechazar imágenes < 1 megapíxel (aprox. < 1000x1000) | Garantiza DPI mínimo para OCR |
| **Guía visual** | Mostrar rectángulo de encuadre con texto "encuadrá la factura completa dentro del marco" | Reduce fotos parciales |

**Decisión técnica**: estos controles se ejecutan **en el dispositivo antes del upload**. No consumen recursos de backend y eliminan ~20-30% de las imágenes problemáticas en origen.

---

## 3. Capa 2 — Preprocesamiento de imagen

**Objetivo**: transformar cualquier imagen aceptada en la mejor versión posible para OCR.

### Pipeline de preprocesamiento (secuencial, Cloud Run con OpenCV)

```
Imagen original
  │
  ├─► 2.1 Detección de orientación (Tesseract OSD o modelo custom)
  │        → Rotación a 0°/180° según texto detectado
  │
  ├─► 2.2 Deskew
  │        → Hough Transform para detectar líneas dominantes
  │        → Corregir inclinación (típico: ±5-15°)
  │
  ├─► 2.3 Crop inteligente
  │        → Detectar contorno de la factura (Canny + findContours)
  │        → Perspective transform para rectangularizar
  │
  ├─► 2.4 Mejora de contraste
  │        → CLAHE (Contrast Limited Adaptive Histogram Equalization)
  │        → No binarización agresiva (destruye info para Document AI)
  │
  ├─► 2.5 Denoise
  │        → fastNlMeansDenoising para imágenes con ruido ISO alto
  │        → Aplicar solo si SNR < umbral (no degradar imágenes limpias)
  │
  ├─► 2.6 Upscaling condicional
  │        → Si DPI efectivo < 150, upscale 2x con interpolación bicúbica
  │        → O usar modelo ESRGAN ligero para super-resolución
  │
  └─► 2.7 Quality score final
           → Score compuesto: DPI + blur + contraste + cobertura de texto
           → Si score < threshold_reject → REJECTED (no se procesa OCR)
           → Si score < threshold_warn → flag para revisión prioritaria HITL
```

### Métricas de quality score

| Componente | Peso | Cálculo |
|---|---|---|
| Blur score | 30% | Variance of Laplacian (normalizado 0-1) |
| Resolución efectiva | 25% | DPI estimado basado en tamaño de caracteres detectados |
| Contraste | 20% | Desviación estándar del histograma de grises |
| Cobertura de texto | 15% | % del área de imagen con texto detectado (OCR rápido) |
| Ruido | 10% | Estimación de SNR |

**Umbrales**:
- `quality_score >= 0.7` → procesamiento normal
- `0.4 <= quality_score < 0.7` → procesamiento con flag, prioridad HITL si confidence baja
- `quality_score < 0.4` → REJECTED, notificar usuario para re-captura

---

## 4. Capa 3 — OCR/IDP primario (Document AI)

### Configuración de Document AI Invoice Parser

- **Procesador**: Invoice Parser (procesador especializado, no el genérico).
- **Versión**: usar siempre `pretrained-invoice-v2.0` o superior (verificar disponibilidad en `southamerica-east1`; si no está, usar `us` y aceptar latencia adicional).
- **Configuración del request**:

```python
from google.cloud import documentai_v1 as documentai

def extract_invoice(gcs_uri: str) -> documentai.Document:
    client = documentai.DocumentProcessorServiceClient()

    raw_document = documentai.RawDocument(
        content=read_from_gcs(gcs_uri),
        mime_type="image/jpeg",
    )

    request = documentai.ProcessRequest(
        name=PROCESSOR_NAME,
        raw_document=raw_document,
        # Habilitar OCR de alta calidad
        process_options=documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(
                enable_native_pdf_parsing=True,       # Para PDFs electrónicos
                enable_image_quality_scores=True,      # Feedback de calidad
                advanced_ocr_options=["ENABLE_MATH"],  # Mejor detección numérica
            ),
        ),
    )

    result = client.process_document(request=request)
    return result.document
```

### Campos que Document AI extrae nativamente (Invoice Parser)

| Campo | Entity type en Document AI | Confianza típica |
|---|---|---|
| Proveedor | `supplier_name` | 0.90-0.98 |
| CUIT (Tax ID) | `supplier_tax_id` | 0.85-0.95 |
| Número de factura | `invoice_id` | 0.88-0.96 |
| Fecha de factura | `invoice_date` | 0.92-0.99 |
| Monto neto | `net_amount` | 0.90-0.97 |
| IVA | `total_tax_amount` | 0.88-0.95 |
| Total | `total_amount` | 0.92-0.98 |
| Moneda | `currency` | 0.95-0.99 |
| Line items | `line_item/*` | 0.80-0.92 |

### Campos AR-específicos que Document AI NO extrae nativamente

| Campo | Problema | Solución (Capa 4) |
|---|---|---|
| **Tipo de factura** (A, B, C, M, E) | No es un entity type estándar | Regex + clasificador Vertex AI |
| **CAE** | No reconocido como entity | Regex sobre texto OCR + Vertex AI |
| **CAE vencimiento** | No reconocido | Proximity search cerca del CAE |
| **Punto de venta** (4 dígitos antes del nro) | Mezclado con invoice_id | Parsing con regex AR |
| **Percepciones/retenciones** | Variedad de formatos | Extracción custom con Vertex AI |

---

## 5. Capa 4 — Post-procesamiento ML (Vertex AI)

### Estrategia dual: reglas determinísticas + modelo ML

**5.1 Reglas determinísticas (alta precisión, sin modelo)**

Se aplican sobre el texto OCR completo (no solo entities de Document AI).

```python
import re

# CUIT: exactamente 11 dígitos, formato XX-XXXXXXXX-X
CUIT_PATTERN = re.compile(r'\b(\d{2})[-.\s]?(\d{8})[-.\s]?(\d{1})\b')

# CAE: exactamente 14 dígitos
CAE_PATTERN = re.compile(r'\b(\d{14})\b')

# Tipo de factura: letra grande prominente (A, B, C, M, E)
# Se busca en el contexto "FACTURA" o "NOTA DE CRÉDITO/DÉBITO"
TIPO_FACTURA_PATTERN = re.compile(
    r'(?:FACTURA|NOTA\s+DE\s+(?:CR[ÉE]DITO|D[ÉE]BITO))\s*(?:TIPO\s*)?([ABCME])\b',
    re.IGNORECASE
)

# Punto de venta + número: XXXX-XXXXXXXX
PV_NUMERO_PATTERN = re.compile(r'\b(\d{4,5})[-.\s](\d{8})\b')

# Fechas argentinas: DD/MM/YYYY o DD-MM-YYYY
FECHA_AR_PATTERN = re.compile(r'\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b')
```

**5.2 Modelo Vertex AI para campos difíciles**

- **Tipo**: modelo de clasificación/extracción entrenado con AutoML o fine-tuning de modelo base.
- **Input**: texto OCR completo + bounding boxes de Document AI.
- **Output**: campos AR-específicos con confidence score.
- **Training data**: correcciones HITL (feedback loop).

**Flujo de decisión por campo**:

```
Para cada campo extraído:
  │
  ├─ Document AI lo extrajo con confidence >= 0.90?
  │    └─ SÍ → usar valor de Document AI
  │
  ├─ Document AI lo extrajo con confidence < 0.90?
  │    └─ Intentar regex sobre texto OCR
  │         ├─ Regex matchea → comparar con Document AI
  │         │    ├─ Coinciden → subir confidence a max(docai, 0.90)
  │         │    └─ No coinciden → flag para HITL, usar el de mayor confianza
  │         └─ Regex no matchea → mantener Document AI, flag si < 0.85
  │
  └─ Document AI NO lo extrajo?
       └─ Intentar regex → Intentar Vertex AI
            ├─ Alguno lo encuentra → usar con su confidence
            └─ Ninguno lo encuentra → campo vacío, flag HITL obligatorio
```

### 5.3 Consensus scoring (votación entre motores)

Para campos críticos (`supplier_cuit`, `total_amount`, `invoice_number`), se usa **triple extracción**:

| Motor | Rol |
|---|---|
| Document AI Invoice Parser | Extracción primaria |
| Regex sobre texto OCR | Validación determinística |
| Vertex AI custom | Extracción secundaria ML |

**Regla de consenso**:
- 3/3 coinciden → `confidence = max(individual_confidences) + 0.02` (cap 0.99)
- 2/3 coinciden → usar el valor mayoritario, `confidence = promedio de los 2`
- 0/3 coinciden → `confidence = 0.0`, **HITL obligatorio**

**Esto es clave para los campos más sensibles**: CUIT del proveedor, monto total, y número de factura. Un error en cualquiera de estos corrompe el asiento SAP.

---

## 6. Capa 5 — Validaciones cruzadas

Las validaciones cruzadas no dependen de ningún modelo ML. Son **reglas de negocio determinísticas** que atrapan errores que el OCR no puede detectar.

### 6.1 Validaciones aritméticas

| Validación | Regla | Tolerancia |
|---|---|---|
| **IVA = neto * alícuota** | `abs(vat_amount - net_amount * alicuota) <= tolerancia` | $1 ARS o 0.5% del neto (el mayor) |
| **Total = neto + IVA + percepciones** | `abs(total - (net + vat + percepciones)) <= tolerancia` | $1 ARS |
| **Sum de line items = neto** | `abs(sum(items.subtotal) - net_amount) <= tolerancia` | $1 ARS |
| **Alícuota coherente** | Si factura tipo A, la alícuota debe ser 10.5%, 21% o 27% | Exacto |

### 6.2 Validaciones fiscales

| Validación | Regla |
|---|---|
| **CUIT módulo 11** | Algoritmo estándar AFIP. Si falla, el CUIT está mal extraído → HITL |
| **CUIT existe** | (Opcional) Consulta al padrón AFIP para verificar que el CUIT está activo |
| **CAE formato** | 14 dígitos exactos |
| **CAE vigencia** | `cae_due_date >= invoice_date` |
| **CAE válido** | (Opcional) Consulta WSCDC de AFIP |
| **Fecha razonable** | `invoice_date` no puede ser futura ni > 1 año de antigüedad |
| **Tipo factura vs condición IVA** | Factura A → proveedor debe ser Responsable Inscripto |

### 6.3 Validaciones de duplicados

```sql
-- Detector de duplicados en Cloud SQL
SELECT COUNT(*) FROM documents
WHERE supplier_cuit = :cuit
  AND invoice_type = :type
  AND invoice_number = :number
  AND status NOT IN ('REJECTED', 'DUPLICATE')
```

Si existe match → marcar como posible duplicado → HITL con referencia al documento original.

### 6.4 Impacto en confidence

Cada validación fallida **reduce el confidence score del campo afectado**:

```python
def apply_validation_penalties(fields: dict, validations: dict) -> dict:
    """Ajusta confidence scores basado en validaciones cruzadas."""

    if not validations["cuit_mod11_valid"]:
        fields["supplier_cuit"]["confidence"] *= 0.5  # Penalización severa

    if not validations["vat_consistent"]:
        fields["vat_amount"]["confidence"] *= 0.7
        fields["net_amount"]["confidence"] *= 0.7

    if not validations["totals_consistent"]:
        fields["total_amount"]["confidence"] *= 0.6
        fields["net_amount"]["confidence"] *= 0.7
        fields["vat_amount"]["confidence"] *= 0.7

    if validations["is_duplicate"]:
        # No penaliza confidence, pero marca para revisión
        fields["_flags"].append("POSSIBLE_DUPLICATE")

    return fields
```

---

## 7. Capa 6 — Confidence scoring y routing

### 7.1 Confidence score final por documento

El score final del documento es una función del **campo con menor confidence** (weakest link), no el promedio:

```python
def compute_document_confidence(fields: dict) -> float:
    """El documento es tan confiable como su campo más débil."""
    required_fields = [
        "supplier_cuit", "supplier_name", "invoice_type",
        "invoice_number", "invoice_date", "net_amount",
        "vat_amount", "total_amount", "cae"
    ]
    confidences = [
        fields[f]["confidence"]
        for f in required_fields
        if f in fields and fields[f]["value"] is not None
    ]

    if not confidences:
        return 0.0

    # Weakest link: el mínimo, no el promedio
    return min(confidences)
```

**Justificación**: si `total_amount` tiene 0.99 de confianza pero `supplier_cuit` tiene 0.60, el documento NO es confiable para carga a SAP. El promedio (0.80) escondería el problema.

### 7.2 Umbrales de routing

| Document confidence | Acción | % estimado del volumen |
|---|---|---|
| `>= 0.90` y todas las validaciones OK | **AUTO-APPROVE** → directo a SAP | ~70-80% |
| `>= 0.75` y < `0.90`, o 1-2 validaciones warn | **HITL-STANDARD** → cola normal de revisión | ~15-20% |
| `< 0.75` o validación crítica fallida | **HITL-PRIORITY** → cola prioritaria | ~5-8% |
| `< 0.40` o imagen REJECTED | **AUTO-REJECT** → notificar re-captura | ~2-5% |

**Los umbrales son configurables por campo y por cliente**. En la POC se arrancan conservadores (0.90 para auto-approve) y se ajustan con datos reales.

### 7.3 Reglas de override (nunca auto-approve si...)

Independiente del confidence score, el documento **siempre va a HITL** si:

- CUIT falla validación módulo 11.
- El total es incoherente con neto + IVA (diferencia > $10 ARS).
- Es posible duplicado.
- El monto total supera un umbral configurable (ej: > $1.000.000 ARS).
- Es la primera factura de un proveedor nuevo (no existe en histórico).

Estas reglas existen porque **un error en estos casos tiene impacto financiero directo**.

---

## 8. Capa 7 — HITL y feedback loop

### 8.1 Interfaz de revisión

```
┌──────────────────────────────────────────────────────────────────┐
│  REVISIÓN DE FACTURA #550e8400          Estado: HITL-STANDARD    │
├─────────────────────────┬────────────────────────────────────────┤
│                         │  Proveedor: Distribuidora Norte S.A.  │
│   [Imagen original]     │  CUIT: 30-71234567-9  ✓               │
│   con zoom y pan        │  Tipo: A  ⚠ (confidence: 0.82)        │
│                         │  Número: 0003-00012345  ✓              │
│   Áreas resaltadas      │  Fecha: 15/03/2026  ✓                 │
│   donde se extrajo      │  Neto: $150.000,00  ✓                 │
│   cada campo            │  IVA: $31.500,00  ✓                   │
│   (bounding boxes)      │  Total: $181.500,00  ✓                │
│                         │  CAE: 73241567890123  ✓                │
│                         │                                        │
│                         │  ⚠ Motivo revisión: Tipo factura       │
│                         │    confidence 0.82 < 0.90              │
│                         │                                        │
│                         │  [Aprobar] [Corregir] [Rechazar]       │
└─────────────────────────┴────────────────────────────────────────┘
```

**Funcionalidades clave**:
- Click en un campo → se resalta el bounding box en la imagen.
- Campo editable: el revisor puede corregir el valor.
- Motivo de revisión visible (por qué llegó a HITL).
- Atajos de teclado para aprobar/rechazar rápido.
- Timer visible del SLA de revisión.

### 8.2 Feedback loop para reentrenamiento

Cada corrección humana genera un **training sample**:

```json
{
  "document_id": "550e8400",
  "correction": {
    "field": "invoice_type",
    "original_value": "B",
    "original_confidence": 0.82,
    "corrected_value": "A",
    "corrected_by": "reviewer@empresa.com",
    "corrected_at": "2026-04-10T16:00:00Z"
  },
  "image_gcs_uri": "gs://triunfo-prod-processed/550e8400.jpg",
  "ocr_text_gcs_uri": "gs://triunfo-prod-ocr/550e8400.json"
}
```

**Ciclo de reentrenamiento**:

```
Correcciones HITL (acumuladas)
        │
        ▼ (cada 500 correcciones o 1 vez por semana)
Vertex AI Training Pipeline
        │
        ├─► Evaluar nuevo modelo contra golden set
        │      ├─ Accuracy mejora → deploy como nuevo endpoint
        │      └─ Accuracy empeora o igual → descartar, investigar
        │
        └─► Actualizar reglas de regex si se detectan patrones recurrentes
```

**Protección contra drift**: el nuevo modelo **siempre** se evalúa contra el golden set antes de desplegarse. Si la accuracy en el golden set baja, no se deploya.

---

## 9. Metodología de medición de precisión

### 9.1 Golden set

| Aspecto | Detalle |
|---|---|
| **Tamaño** | 500 facturas (POC: 100, Piloto: 300, Prod: 500) |
| **Composición** | 40% buena calidad, 30% calidad media, 30% baja calidad |
| **Tipos** | Facturas A (50%), B (30%), C (10%), NC/ND (10%) |
| **Anotación** | Cada campo anotado manualmente por 2 personas independientes. Discrepancias resueltas por un tercero |
| **Actualización** | Se agregan 50 facturas nuevas por mes, se retiran las más antiguas |
| **Almacenamiento** | Bucket separado con acceso restringido, no accesible por los modelos de entrenamiento |

### 9.2 Métricas de precisión

| Métrica | Definición | Target |
|---|---|---|
| **Field-level accuracy** | % de campos donde el valor extraído coincide exactamente con el ground truth | > 95% promedio, > 97% en imagen buena calidad |
| **Character-level accuracy** | % de caracteres correctos en campos de texto (para medir OCR puro) | > 99% |
| **Field-level precision** | TP / (TP + FP) — de los campos aceptados como correctos, cuántos realmente lo son | > 99% (el más crítico) |
| **Field-level recall** | TP / (TP + FN) — de los campos correctos, cuántos fueron aceptados automáticamente | > 85% (balance con STP) |
| **Document-level STP accuracy** | % de documentos auto-aprobados que están 100% correctos | > 99% |
| **Detection rate** | % de errores de extracción que fueron detectados (por validación o confidence) | > 98% |

### 9.3 Cómo se calcula la accuracy de un campo

```python
def field_matches(extracted: str, ground_truth: str, field_type: str) -> bool:
    """Comparación exacta con normalización por tipo de campo."""

    if field_type == "amount":
        # Numérico: tolerancia de $0.01
        return abs(float(extracted) - float(ground_truth)) < 0.01

    if field_type == "date":
        # Fecha: comparar como date objects
        return parse_date(extracted) == parse_date(ground_truth)

    if field_type == "cuit":
        # CUIT: solo dígitos, sin guiones
        return digits_only(extracted) == digits_only(ground_truth)

    # Texto: normalizado (lowercase, strip, collapse spaces)
    return normalize(extracted) == normalize(ground_truth)
```

### 9.4 Dashboard de precisión

Métricas visibles en tiempo real en Cloud Monitoring:

```
┌─────────────────────────────────────────────────────────────┐
│  PRECISION DASHBOARD — Últimas 24h                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Documents processed:  487                                  │
│  Auto-approved (STP):  361 (74.1%)  ████████████░░░░        │
│  Sent to HITL:          98 (20.1%)  ████░░░░░░░░░░░░        │
│  Auto-rejected:         28 (5.7%)   █░░░░░░░░░░░░░░░        │
│                                                             │
│  Field accuracy (auto-approved):                            │
│    supplier_cuit:    99.2%  ████████████████████░            │
│    total_amount:     98.4%  ███████████████████░░            │
│    invoice_number:   97.8%  ███████████████████░░            │
│    invoice_date:     99.5%  ████████████████████░            │
│    net_amount:       97.1%  ███████████████████░░            │
│    vat_amount:       96.8%  ███████████████████░░            │
│    invoice_type:     95.3%  ███████████████████░░            │
│    cae:              94.7%  ██████████████████░░░   ⚠        │
│                                                             │
│  HITL correction rate: 12.3% (de los docs que entran a HITL)│
│  Avg HITL review time: 45 sec                               │
│  SAP load success:     99.1%                                │
│                                                             │
│  ⚠ ALERTA: CAE accuracy < 95% — revisar extracción         │
└─────────────────────────────────────────────────────────────┘
```

### 9.5 Ejecución de tests de precisión

| Test | Frecuencia | Automatización |
|---|---|---|
| **Golden set completo** | Cada release / cada semana | Cloud Build pipeline: corre el golden set, compara resultados, falla el deploy si accuracy < target |
| **Smoke test** | Cada deploy | 10 facturas de referencia, verificación exacta |
| **A/B testing** | Cuando se cambia modelo | Mismo input a modelo viejo y nuevo, comparar field-level accuracy |
| **Regression test** | Cada retrain de Vertex AI | Golden set + últimas 100 correcciones HITL |
| **Drift monitoring** | Continuo (diario) | Comparar distribución de confidence scores contra baseline. Si el P50 de confidence baja > 5%, alerta |

---

## 10. Casos especiales y su tratamiento

### 10.1 Facturas con múltiples páginas

- Document AI procesa multi-page nativo en PDF.
- Para fotos sueltas (ej: 2 fotos de la misma factura): el usuario debe indicar agrupación en la UI, o se implementa detección automática por `supplier_cuit + fecha + monto parcial`.

### 10.2 Notas de crédito y débito

- Mismos campos que factura, pero `invoice_type` incluye NC-A, NC-B, ND-A, ND-B.
- El monto en SAP se carga como negativo (nota de crédito) o positivo (nota de débito).
- Validación adicional: una NC debe referenciar una factura existente.

### 10.3 Facturas en moneda extranjera

- Campo `currency` detectado por Document AI.
- Si `currency = USD`, se requiere tipo de cambio (manual o consultado a BCRA API).
- SAP recibe el monto en moneda original + tipo de cambio.

### 10.4 Facturas electrónicas (PDF de AFIP)

- Son PDFs nativos con texto embebido → no necesitan OCR, solo parsing.
- Document AI con `enable_native_pdf_parsing=True` extrae sin degradación.
- Accuracy esperada: **>99%** (texto es digital, no hay error de reconocimiento).
- **Oportunidad**: si el cliente tiene mix de fotos + PDFs electrónicos, los PDFs suben el promedio general de accuracy significativamente.

---

## 11. Resumen de decisiones técnicas para precisión

| # | Decisión | Justificación |
|---|---|---|
| D-01 | Captura guiada con detección de blur/bordes en dispositivo | Eliminar basura antes del pipeline. Foto buena = OCR bueno |
| D-02 | Preprocesamiento completo (deskew, denoise, CLAHE) en Cloud Run | Maximizar legibilidad sin destruir información |
| D-03 | Document AI Invoice Parser como motor primario | Mejor accuracy en facturas vs Vision OCR genérico |
| D-04 | Triple extracción para campos críticos (DocAI + regex + Vertex AI) | Consenso reduce error en CUIT, total, nro factura |
| D-05 | Confidence = min(campos) no promedio | Evitar que un campo malo se esconda detrás de un promedio alto |
| D-06 | Validaciones cruzadas que penalizan confidence | Atrapar errores aritméticos/fiscales que el OCR no puede detectar |
| D-07 | Override rules para HITL obligatorio | Nunca auto-aprobar si CUIT inválido, total incoherente, o duplicado |
| D-08 | Feedback loop con reentrenamiento protegido | Mejorar continuamente pero nunca degradar (golden set gate) |
| D-09 | Umbrales conservadores iniciales, ajuste con datos | Arrancar con auto-approve en 0.90, bajar solo si la data lo justifica |
| D-10 | Golden set con anotación doble-ciego | Medición de precisión confiable, no sesgada por el sistema |
