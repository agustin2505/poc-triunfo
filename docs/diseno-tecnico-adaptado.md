# Triunfo — Diseño Técnico Adaptado: Pipeline Flexible de Facturas Multi-Proveedor

> **Versión:** 1.1 — Adaptado para múltiples formatos, impuestos locales y proveedores no-AFIP  
> **Fecha:** 2026-04-13  
> **Estado:** Draft para revisión y ajustes  
> **Stack principal:** Google Cloud Platform + SAP

---

## Spec 1 — Contexto y Alcance Actualizado

### 1.1 Cambios respecto al diseño original

**Antes (Original)**:
- Enfoque exclusivo en facturas AFIP argentinas (Tipo A/B/C, CAE, CUIT validación mod 11)
- Validaciones fiscales rígidas por norma AFIP
- Un esquema de campos único

**Ahora (Adaptado)**:
- Facturas de **servicios** (luz, gas, agua, internet) — Edenor, Metrogas, AySA, Aguas Argentinas, Telecom, etc.
- Facturas de **negocios** que emiten servicios/productos propios
- Múltiples **formatos e impuestos por localidad** (varía por provincia/municipio)
- **Agnóstico a AFIP** — validaciones genéricas, no dependientes de organismos fiscales específicos
- Soporte para **múltiples sedes** con diferentes contextos de impuestos

### 1.2 Objetivo principal (REVISADO)

Automatizar la ingesta, extracción y carga a SAP de **facturas y comprobantes de proveedores variados**, logrando:

- **Alta precisión** (>95% accuracy por campo, independiente del formato)
- **Flexibilidad** para absorber nuevos proveedores y formatos sin redesign
- **Trazabilidad** completa desde imagen original hasta asiento SAP
- **Reducción de carga manual** (target: >70% STP)
- **Gestión multi-sede** con contextos de impuestos configurables

### 1.3 Tipos de documentos en alcance

| Tipo | Ejemplos | Campos típicos | Variabilidad |
|---|---|---|---|
| **Servicios esenciales** | Luz (Edenor, Edelap), Gas (Metrogas), Agua (AySA), Internet (Telecom, Claro) | Período, consumo, tarifa, total, vencimiento | **Alta** — cada proveedor/provincia tiene formato propio |
| **Facturas de negocio** | Venta de productos/servicios de la empresa | Descripción, cantidad, precio unitario, total, impuestos variables | **Media-Alta** — varía por tipo de negocio |
| **Recibos/Comprobantes** | Pagos de alquileres, servicios contratados | Concepto, monto, período, acreedor | **Media** |
| **Documentos fiscales no-AFIP** | Comprobantes de pago, notas de débito/crédito informales | Varía por emisor | **Muy alta** |

### 1.4 Dentro del alcance (REVISADO)

| Módulo | Incluido | Nota |
|---|---|---|
| Ingesta multi-canal (mobile/web/bulk) | Si | - |
| Captura guiada en dispositivo | Si | - |
| Preprocesamiento de imagen | Si | - |
| Clasificación automática de documento | Si | **NUEVO** — determina tipo/proveedor |
| OCR/IDP + extracción de campos | Si | Agnóstico a formato |
| Validaciones genéricas (consistencia, formato) | Si | Sin reglas AFIP |
| Validaciones específicas por proveedor/localidad | Si | **NUEVO** — configurables |
| Flujo HITL (revisión humana) | Si | - |
| Integración SAP (mapeo configurable) | Si | Flexible por sede/tipo |
| Auditoría y trazabilidad | Si | - |
| Observabilidad (métricas, alertas) | Si | - |

### 1.5 Fuera de alcance — Eliminado

- Extracción de estados contables
- Análisis financiero / ratios
- Generación de reportes contables
- **Validaciones AFIP específicas** (CAE, CUIT módulo 11, tipo factura AFIP, etc.)

---

## Spec 2 — Requerimientos Funcionales (ADAPTADOS)

### RF-01: Ingesta de imágenes (SIN CAMBIOS)

- **RF-01.1** — El sistema acepta imágenes en formatos JPEG, PNG, TIFF, PDF (single/multi-page).
- **RF-01.2** — Canales de ingesta:
  - **Mobile**: upload directo vía app/PWA.
  - **Web**: portal con drag & drop.
  - **Bulk**: carga masiva vía Cloud Storage.
- **RF-01.3** — Cada documento recibe `document_id` (UUID v4).
- **RF-01.4** — Metadatos: timestamp, canal, usuario, tamaño, hash SHA-256, **sede_id** (NUEVO).

### RF-02: Captura guiada en dispositivo (SIN CAMBIOS)

- Detección de blur, bordes, iluminación, resolución mínima.
- Guía visual para encuadre correcto.
- Rechazo en origen de imágenes irrecuperables.

### RF-03: Clasificación automática de documento (NUEVO)

**RF-03.1** — El sistema clasifica cada imagen antes de extracción:

```
Clasificación en 2 niveles:

NIVEL 1: Categoría general
├── SERVICIOS (luz, gas, agua, internet, teléfono)
├── FACTURA_NEGOCIO (documentos que emite la empresa)
├── RECIBO
├── COMPROBANTE_FISCAL
└── OTRO (requiere HITL obligatoria para clasificación manual)

NIVEL 2: Proveedor específico (si aplica)
├── Edenor, Edelap, ... (luz)
├── Metrogas, YPF Gas, ... (gas)
├── AySA, Aguas Argentinas, ... (agua)
├── Telecom, Claro, ... (internet/telecom)
└── [Proveedor interno] (factura negocio)
```

**RF-03.2** — Método de clasificación:
- Extracción rápida de texto OCR (no Document AI full)
- Búsqueda de patrones: nombre de proveedor, logos, palabras clave ("factura de luz", "consumo", "período", etc.)
- Modelo ML ligero (Vertex AI) entrenado con ejemplos de cada tipo
- Confidence score de clasificación; si < 0.70, enviar a HITL con clasificación sugerida

**RF-03.3** — Output: `{document_id, category, provider, classification_confidence}`

### RF-04: Extracción de campos (ADAPTADO)

**RF-04.1** — La extracción es **agnóstica a formato**. Según la categoría y proveedor, el sistema:
- Activa un **schema de campos específico** para esa categoría/proveedor
- Aplica reglas de extracción personalizadas

**RF-04.2** — Campos **universales** (extraer siempre):

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `document_type` | enum | Si | FACTURA_SERVICIO, FACTURA_NEGOCIO, RECIBO, COMPROBANTE, etc. |
| `provider_name` | string | Si | Nombre de quien emite el documento |
| `provider_tax_id` | string | No | CUIT/CUIL si existe (pero NO validar AFIP) |
| `issue_date` | date | Si | Fecha de emisión |
| `period_start` | date | No | Período de consumo/servicio (ej: 01/03 a 31/03) |
| `period_end` | date | No | - |
| `total_amount` | decimal | Si | Monto total a pagar |
| `currency` | enum (ARS, USD) | Si | Moneda |
| `vat_amount` | decimal | No | IVA (puede no estar en facturas de servicios) |
| `tax_code` | string | No | Código de impuesto local (configurable por sede) |
| `due_date` | date | No | Fecha de vencimiento |
| `reference_number` | string | No | Número de factura, comprobante, o referencia interna |
| `location` | string | No | Localidad/provincia donde se aplicó el servicio |

**RF-04.3** — Campos **específicos por categoria** (ej: para servicios esenciales):

| Campo | Tipo | Categoría | Ejemplo |
|---|---|---|---|
| `consumption_value` | decimal | SERVICIOS | 250 kWh, 500 m³ |
| `consumption_unit` | string | SERVICIOS | kWh, m³, litros |
| `meter_reading_start` | decimal | SERVICIOS | 45230 |
| `meter_reading_end` | decimal | SERVICIOS | 45480 |
| `tariff_code` | string | SERVICIOS | T1, R1, etc. (varía por proveedor) |
| `basic_charge` | decimal | SERVICIOS | Costo fijo del período |
| `consumption_charge` | decimal | SERVICIOS | Costo variable por consumo |
| `other_charges` | array | SERVICIOS | Mantenimiento, conexión, etc. |
| `line_items` | array | FACTURA_NEGOCIO | [{description, quantity, unit_price, total}, ...] |

**RF-04.4** — Motor de extracción:
- Document AI como base (genérico)
- **Vertex AI custom** con fine-tune por categoría/proveedor
- **Regex específica** por patrón (ej: lectura de medidores, períodos)
- Post-procesamiento con reglas by provider

### RF-05: Validaciones genéricas (SIN AFIP, ADAPTADAS)

**RF-05.1** — Validaciones **universales** (aplican a todo documento):

| Validación | Regla | Tolerancia |
|---|---|---|
| **Consistencia aritmética** | Si hay descomposición de montos (básico + consumo + IVA + otros), verificar suma | $1 ARS o 0.5% del total |
| **Formato de monto** | Total es número válido, positivo | - |
| **Fechas lógicas** | `issue_date <= due_date` (si ambas existen); `issue_date` no futura | - |
| **Período coherente** | Si `period_start` y `period_end` existen, `start < end` | - |
| **Moneda válida** | ARS o USD (configurable por sede) | - |
| **Duplicados** | Mismo `reference_number + provider + issue_date` en histórico | - |

**RF-05.2** — Validaciones **específicas por proveedor** (configurables en BD):

Ejemplo para **Edenor** (luz):
```json
{
  "provider": "Edenor",
  "validations": [
    {
      "name": "meter_reading_consistency",
      "rule": "meter_reading_end >= meter_reading_start",
      "penalty_if_fail": 0.3  // reduce confidence en 30%
    },
    {
      "name": "consumption_coherence",
      "rule": "abs((meter_reading_end - meter_reading_start) - consumption_value) < 10",
      "penalty_if_fail": 0.2
    },
    {
      "name": "tariff_known",
      "rule": "tariff_code in ['T1', 'R1', 'R2', 'R3']",  // valores conocidos para Edenor
      "penalty_if_fail": 0.15
    }
  ]
}
```

**RF-05.3** — **Sin validaciones AFIP**:
- ~~CUIT módulo 11~~
- ~~CAE~~
- ~~Tipo de factura AFIP (A/B/C)~~
- ~~Consultas a padrón AFIP~~

---

## Spec 3 — Arquitectura Multi-Proveedor

### 3.1 Nuevo componente: Catálogo de Proveedores

```
Cloud SQL tabla: providers_catalog
├── provider_id (PK)
├── provider_name
├── category (SERVICIOS, FACTURA_NEGOCIO, etc.)
├── document_format_type (Edenor-2024, Metrogas-2023, etc.)
├── logo_gcs_uri (para clasificación visual)
├── keywords (["luz", "consumo", "Edenor", ...])
├── extraction_schema (JSON: qué campos esperar)
├── validation_rules (JSON: reglas específicas)
├── sap_mapping (JSON: cómo mapear a SAP para este proveedor)
├── sede_ids (array: qué sedes usan este proveedor)
├── active (bool)
└── last_updated

Ejemplo row:
{
  "provider_id": "edenor-001",
  "provider_name": "Edenor",
  "category": "SERVICIOS",
  "document_format_type": "Edenor-2024-v1",
  "keywords": ["edenor", "luz", "energía", "consumo", "kWh"],
  "extraction_schema": {
    "required_fields": ["meter_reading_start", "meter_reading_end", "consumption_value", "total_amount"],
    "optional_fields": ["basic_charge", "tax_code", "period_start", "period_end"]
  },
  "validation_rules": {
    "meter_reading_consistency": {...},
    "consumption_coherence": {...}
  },
  "sap_mapping": {
    "provider_name": "VENDOR.NAME",
    "total_amount": "ITEM.GROSS_AMOUNT",
    "consumption_value": "CUSTOM_FIELD_1"
  }
}
```

### 3.2 Nuevo componente: Configuración por Sede

```
Cloud SQL tabla: sede_configuration
├── sede_id (PK)
├── sede_name
├── location (provincia/región)
├── country
├── currency (ARS, USD)
├── tax_rules (JSON: impuestos específicos de esa provincia)
├── enabled_providers (array: qué proveedores aplican aquí)
├── sap_company_code (ej: "1000" para SAP)
├── hitl_language (es, en, pt)
├── hitl_review_sla_hours (4, 24, etc.)
└── created_at, updated_at

Ejemplo:
{
  "sede_id": "buenosaires-001",
  "sede_name": "Sede Buenos Aires",
  "location": "CABA",
  "currency": "ARS",
  "tax_rules": {
    "vat_percentage": 21.0,
    "local_tax": 3.5,
    "municipality_tax": 1.2
  },
  "enabled_providers": ["edenor-001", "metrogas-001", "aysa-001", "telecom-001"]
}
```

### 3.3 Flujo actualizado de procesamiento

```
┌─────────────────────────────────────────────────────┐
│  INGESTA                                            │
│  Mobile/Web/Bulk → Cloud Storage                    │
│  [document_id, sede_id, timestamp]                  │
└────────────────┬──────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────┐
│  CLASIFICACIÓN (NUEVO)                              │
│  Cloud Run (classifier)                             │
│  1. OCR rápido del documento                        │
│  2. Búsqueda de patrones + ML                       │
│  3. Output: {category, provider, confidence}        │
│  Si confidence < 0.70 → HITL obligatoria            │
└────────────────┬──────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────┐
│  PREPROCESAMIENTO (sin cambios)                     │
│  Cloud Run (preprocessor)                           │
│  - Deskew, denoise, crop, contraste                 │
└────────────────┬──────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────┐
│  EXTRACCIÓN (ADAPTADA)                              │
│  Cloud Run (extractor)                              │
│  1. Busca schema según category + provider          │
│  2. Document AI + Vertex AI custom (by provider)    │
│  3. Regex/rules específicas (by provider)           │
│  4. Output: {fields, confidences, category}         │
└────────────────┬──────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────┐
│  VALIDACIÓN (ADAPTADA)                              │
│  Cloud Run (validator)                              │
│  1. Validaciones genéricas (dupes, aritmética)      │
│  2. Carga validaciones específicas del proveedor    │
│  3. Aplica penalidades de confidence                │
│  4. Routing: AUTO-APPROVE o HITL                    │
└────────────┬──────────────────┬─────────────────────┘
             ▼                  ▼
      AUTO-APPROVE           HITL
         (SAP)          (revisión manual)
         (terminal)          │
                             ▼
                        [UI Firestore]
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
              APPROVED           REJECTED
                    │                 │
                    └────────┬────────┘
                             ▼
                      [SAP LOADER]
```

---

## Spec 4 — Validaciones Genéricas (Sin AFIP)

### 4.1 Validaciones aritméticas

```python
# Suma consistente
def validate_arithmetic_sum(document: dict) -> bool:
    """Verifica que descomposición de montos sea consistente."""
    
    total = document.get("total_amount", 0)
    basic = document.get("basic_charge", 0) or 0
    consumption = document.get("consumption_charge", 0) or 0
    vat = document.get("vat_amount", 0) or 0
    other_charges = sum([c["amount"] for c in document.get("other_charges", [])])
    
    calculated_total = basic + consumption + vat + other_charges
    tolerance = max(1.0, total * 0.005)  # $1 ARS o 0.5% del total
    
    return abs(total - calculated_total) <= tolerance
```

### 4.2 Validaciones de formato e integridad

| Validación | Regla |
|---|---|
| **Montos válidos** | Todos positivos; no más de 2 decimales (ARS) |
| **Fechas lógicas** | issue_date <= due_date; no fechas futuras |
| **Período coherente** | period_start < period_end (si ambas existen) |
| **Consumo positivo** | Si es servicio, consumo > 0 |
| **Duplicados** | Mismo reference + provider + issue_date |
| **Campos requeridos** | Presentes todos los marked as required en el schema |

### 4.3 Validaciones específicas por proveedor (ejemplo)

**Edenor (Luz)**:
```
✓ meter_reading_end > meter_reading_start
✓ (meter_reading_end - meter_reading_start) ≈ consumption_value (tolerancia ±5%)
✓ tariff_code en lista conocida
✓ basic_charge + (consumption_value * rate) ≈ consumption_charge (tolerancia ±$1)
```

**Metrogas (Gas)**:
```
✓ consumption_value > 0
✓ meter_reading_end >= meter_reading_start
✓ IVA (si aplica) coherente con total
```

**Factura Negocio** (interna):
```
✓ sum(line_items.subtotal) ≈ net_amount
✓ net_amount + vat ≈ total_amount
✓ Cada line_item tiene quantity > 0 y unit_price > 0
```

---

## Spec 5 — Confidence Scoring y Routing (ADAPTADO)

### 5.1 Estructura de confidence

Para cada documento se calcula:

```python
{
  "document_confidence": min(field_confidences),  # weakest link
  "classification_confidence": 0.92,
  "field_confidences": {
    "total_amount": 0.98,
    "period_end": 0.85,
    "consumption_value": 0.88,
    # ... etc
  },
  "validation_penalties_applied": [
    {"validation": "meter_reading_consistency", "penalty": 0.3}
  ],
  "final_confidence": 0.55  # después de penalidades
}
```

### 5.2 Umbrales de routing (REVISADOS - más conservadores sin AFIP)

| Rango | Acción | Volumen estimado |
|---|---|---|
| >= 0.88 + sin penalidades críticas | **AUTO-APPROVE** → SAP directo | ~60-70% |
| 0.70-0.88 o 1 validación warning | **HITL-STANDARD** | ~20-25% |
| < 0.70 o validación crítica fallida | **HITL-PRIORITY** | ~8-10% |
| < 0.40 o classificación failure | **AUTO-REJECT** | ~2-5% |

**Notas**:
- Sin AFIP, no hay override rule de "CUIT módulo 11 falla" → más documentos potencialmente auto-approvable
- Pero clasificación fallida (ej: no se identifica el proveedor) siempre → HITL obligatoria

---

## Spec 6 — HITL y Feedback (Sin cambios en estructura, adaptado en contenido)

### 6.1 Interfaz de revisión

```
┌──────────────────────────────────────────────────────────────┐
│  REVISIÓN DE DOCUMENTO #550e8400    Estado: HITL-STANDARD   │
├──────────────────┬─────────────────────────────────────────┤
│   [Imagen]       │ Proveedor: Edenor              ✓         │
│   con zoom       │ Categoría: SERVICIOS (luz)    ✓         │
│   y pan          │ Período: 01/03 - 31/03/2026   ✓         │
│                  │ Lectura inicial: 45230        ⚠ (0.75)  │
│   Áreas          │ Lectura final: 45480          ✓         │
│   resaltadas     │ Consumo: 250 kWh              ✓         │
│   (OCR boxes)    │ Tarifa: T1                    ✓         │
│                  │ Básico: $500                  ✓         │
│   ⚠ Motivo:      │ Consumo: $2.500               ✓         │
│   Lectura        │ IVA: $630                     ✓         │
│   inicial con    │ **TOTAL: $3.630**             ✓         │
│   baja conf.     │                                         │
│                  │ ⚠ Validación: meter reading low conf    │
│                  │                                         │
│                  │ [Aprobar] [Corregir] [Rechazar]         │
└──────────────────┴─────────────────────────────────────────┘
```

### 6.2 Feedback loop

Cada corrección genera training sample para reentrenamiento **por proveedor**:

```json
{
  "document_id": "550e8400",
  "provider_id": "edenor-001",
  "category": "SERVICIOS",
  "correction": {
    "field": "meter_reading_start",
    "original_value": 45280,
    "original_confidence": 0.75,
    "corrected_value": 45230,
    "corrected_by": "reviewer@empresa.com"
  },
  "timestamp": "2026-04-10T16:00:00Z"
}
```

**Ciclo de reentrenamiento** (ahora separado por proveedor):

```
Correcciones HITL para [proveedor_id]
        │ (cada 200 correcciones o 1x por semana)
        ▼
Vertex AI fine-tune (modelo específico por proveedor)
        │
        ├─► Evaluar contra golden set de ese proveedor
        │      ├─ Accuracy mejora → deploy nuevo endpoint
        │      └─ Accuracy no mejora → descartar
        │
        └─► Actualizar reglas regex si se detectan patrones recurrentes
```

---

## Spec 7 — Golden Set y Métricas (ADAPTADO)

### 7.1 Golden set multi-proveedor

| Aspecto | Detalle |
|---|---|
| **Tamaño total** | 300 documentos (POC: 50, Piloto: 150, Prod: 300) |
| **Distribución** | 40% servicios, 40% facturas negocio, 20% otros |
| **Por proveedor** | Min 5 documentos por proveedor (Edenor, Metrogas, AySA, etc.) |
| **Por calidad** | 50% buena, 30% media, 20% baja |
| **Anotación** | Doble-ciego por revisor humano; discrepancias resueltas por tercero |
| **Actualización** | Agregar 30 nuevos documentos/mes |

### 7.2 Métricas de precisión (REVISADAS)

| Métrica | Target | Nota |
|---|---|---|
| **Field-level accuracy** | > 95% promedio | Exactitud exacta (para montos, +/- $0.01) |
| **Character-level accuracy** | > 99% | OCR puro sin post-procesamiento |
| **Field-level precision** | > 98% | Falso positivo < 1% (crítico) |
| **Document-level STP accuracy** | > 98% | Auto-aprobados 100% correctos |
| **Clasificación accuracy** | > 95% | Categoría + proveedor correctos |
| **Validación detection rate** | > 95% | Errores detectados por validaciones |

### 7.3 Dashboard de precisión (REVISADO)

```
┌──────────────────────────────────────────────────────┐
│  PRECISION DASHBOARD — Últimas 24h                  │
├──────────────────────────────────────────────────────┤
│                                                     │
│  Documents processed:        487                    │
│  Auto-approved (STP):        342 (70.2%)  ████████ │
│  Sent to HITL:               123 (25.3%)  ███░░░░░ │
│  Auto-rejected:               22 (4.5%)   █░░░░░░░ │
│                                                     │
│  CLASSIFICATION ACCURACY:                           │
│    Edenor:      96.3%  ✓                           │
│    Metrogas:    94.1%  ⚠                           │
│    AySA:        97.8%  ✓                           │
│    Interno:     99.2%  ✓                           │
│                                                     │
│  FIELD ACCURACY (auto-approved):                    │
│    provider_name:       99.8%  ████████████████████ │
│    total_amount:        98.1%  ██████████████████░░ │
│    period_end:          96.7%  ██████████████████░░ │
│    consumption_value:   95.2%  █████████████████░░░ │
│    tax_code:            93.4%  ███████████████░░░░░ │
│                                                     │
│  HITL correction rate:        8.9%                 │
│  Avg HITL review time:        38 sec               │
│  SAP load success:            99.3%                │
│                                                     │
│  ⚠ ALERTA: Metrogas classification accuracy < 95% │
│    → Revisar training data, posibles nuevos formatos
└──────────────────────────────────────────────────────┘
```

---

## Spec 8 — SAP Mapping Flexible

### 8.1 Mapeo dinámico por proveedor/tipo

En lugar de un mapeo único, cada proveedor/categoría tiene su propio mapeo:

```
Cloud SQL tabla: sap_mappings
├── mapping_id (PK)
├── provider_id (FK)
├── categoria
├── sede_id (FK)
├── mapping_json (objeto que mapea Triunfo → SAP)
├── active (bool)
└── version

Ejemplo para Edenor:
{
  "mapping_json": {
    "HEADERDATA": {
      "DOC_TYPE": "RE",  // Recibo
      "COMP_CODE": "${sede.sap_company_code}",
      "CURRENCY": "${sede.currency}",
      "GROSS_AMOUNT": "${total_amount}",
      "REF_DOC_NO": "${reference_number} (${provider_name} - ${period_end})"
    },
    "ADDRESSDATA": {
      "NAME": "${provider_name}",
      "CITY": "${location}"
    },
    "ITEMDATA": [
      {
        "INVOICE_DOC_ITEM": "0001",
        "ITEM_AMOUNT": "${basic_charge}",
        "GL_ACCOUNT": "4010001",  // Servicios básicos - luz
        "COST_CENTER": "${sede_id}"
      },
      {
        "INVOICE_DOC_ITEM": "0002",
        "ITEM_AMOUNT": "${consumption_charge}",
        "GL_ACCOUNT": "4010002"
      }
    ]
  }
}

Ejemplo para Factura Negocio (interna):
{
  "mapping_json": {
    "ITEMDATA": "from_line_items",  // Loop sobre line_items
    "GL_ACCOUNT": "by_product_type"  // Buscar account según descripción
  }
}
```

### 8.2 SAP Integration (sin cambios en archit.)

- OData, IDoc o RFC según config del cliente
- Retry con backoff exponencial
- Almacenar SAP_DOCUMENT_NUMBER
- Si falla → estado SAP_ERROR con detalles

---

## Spec 9 — Roadmap adaptado por fases

### Fase 1: POC (6-8 semanas)

**Objetivo**: Validar que el pipeline flexible maneja 2-3 proveedores reales correctamente.

| Entregable | Detalle |
|---|---|
| Pipeline mínimo | Ingesta → Clasificación → Extracción → Validación → HITL mock |
| Catálogo de 3 proveedores | Edenor, Metrogas, Factura Interna (ejemplos) |
| Golden set multi-proveedor | 50 documentos (20 por proveedor principal + otros) |
| Accuracy por proveedor | Report field-level accuracy separado por provider |
| Mock SAP | Endpoint que valida mapeos configurables |

**Criterios de salida**:
- Accuracy > 90% por campo en cada proveedor probado
- Clasificación > 90% accuracy
- Pipeline ejecuta sin errores en 85% de documentos
- Latencia < 40 segundos P95

**Riesgos**:
- Formatos muy variados entre proveedores → Mitigación: testear 10 muestras de cada uno al día 3
- Campos AR-específicos no encontrados → Mitigación: validar con cliente qué campos son críticos

### Fase 2: Piloto (10-12 semanas)

**Objetivo**: Operar con 5-7 proveedores reales, HITL funcional, SAP real.

| Entregable | Detalle |
|---|---|
| Catálogo expandido | +5 proveedores (agua, internet, otros servicios) |
| UI HITL completa | Revisión lado a lado, edición de campos, routing |
| Preprocesamiento optimizado | Por tipo de documento (servicios vs negocio) |
| Vertex AI fine-tune por provider | Modelo custom para cada proveedor del catálogo |
| SAP real | Integración sandbox → sandbox (sin producción) |
| Multi-sede config | 2-3 sedes con impuestos diferentes |

---

## Spec 10 — Decisiones técnicas clave (NUEVAS)

| # | Decisión | Justificación |
|---|---|---|
| D-01 | Catálogo de proveedores en BD | Permite agregar nuevos sin redeploy; configuración vía UI |
| D-02 | Schema de campos dinámica por provider | Algunos tienen "lectura de medidor", otros "línea items"; no fuerza 1 estructura |
| D-03 | Clasificación como etapa separada | Documenta qué es cada factura; entrada para elegir extractor específico |
| D-04 | Validaciones genéricas + específicas por provider | Reutilizable, pero permite customización sin código |
| D-05 | Mapeo SAP por provider/categoria en tabla | No hardcodear en código; cliente puede actualizar sin deploy |
| D-06 | Sin validaciones AFIP | Agnóstico a regulaciones específicas; flexible para múltiples contextos |
| D-07 | Confidence = min(campos) como antes | Sigue siendo "weakest link", no promedio |
| D-08 | Reentrenamiento separado por provider | Evita que mejoras de Edenor interfieran con Metrogas |
| D-09 | Soporte multi-sede en arquitectura base | Sed es parámetro en llamadas; permite diferentes impuestos/proveedores por región |
| D-10 | Golden set multi-proveedor desde POC | Evita surpresas de accuracy en piloto; datos realistas desde el inicio |

---

## Resumen: Cambios principales del diseño original

| Aspecto | Original | Adaptado |
|---|---|---|
| **Scope** | Facturas AFIP argentinas | Múltiples formatos, proveedores, impuestos locales |
| **Clasificación** | N/A | ✅ Etapa nueva de clasificación automática |
| **Validaciones** | AFIP-specific (CUIT mod 11, CAE) | Genéricas + específicas por proveedor |
| **Schema de campos** | Único para todas las facturas | Dinámico por categoría/proveedor |
| **Configuración** | En código | ✅ En BD (catálogo, validaciones, mappings) |
| **Multi-sede** | No considerado | ✅ Soporte nativo con contextos de impuestos |
| **Reentrenamiento ML** | Único modelo | ✅ Separado por proveedor |
| **Golden set** | 100 facturas de una tipo | 50-300 multi-proveedor |
| **SAP mapping** | Hardcoded | ✅ Tablas configurables |
| **Infraestructura** | Sin cambios | Sin cambios (GCP, Pub/Sub, Cloud Run) |

