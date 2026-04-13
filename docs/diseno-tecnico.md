# Triunfo — Diseño Técnico: Pipeline de Facturas con OCR/IDP y Carga a SAP

> **Versión:** 1.0  
> **Fecha:** 2026-04-10  
> **Estado:** Draft para revisión  
> **Stack principal:** Google Cloud Platform + SAP

---

## Spec 1 — Contexto y Alcance

### 1.1 Contexto

El sistema existente extrae datos de estados contables. El nuevo proyecto **Triunfo** reemplaza ese alcance y se enfoca exclusivamente en:

- Captura de **fotos de facturas** (incluyendo imágenes de baja calidad desde móvil).
- Extracción automática de campos mediante **OCR/IDP**.
- Validación fiscal argentina (CUIT, IVA, totales).
- **Carga automatizada a SAP** con trazabilidad completa.

### 1.2 Objetivo principal

Automatizar de punta a punta la carga de facturas de proveedores en SAP, logrando:

- **Alta precisión** (>95% accuracy por campo en condiciones normales).
- **Trazabilidad** completa desde la imagen original hasta el asiento SAP.
- **Reducción de carga manual** (target: >70% STP — Straight-Through Processing).

### 1.3 Dentro del alcance

| Módulo | Incluido |
|---|---|
| Ingesta de imágenes (mobile/web/bulk) | Si |
| Preprocesamiento de imagen | Si |
| OCR/IDP + extracción de campos | Si |
| Validaciones fiscales (CUIT, IVA, totales) | Si |
| Flujo HITL (revisión humana) | Si |
| Integración SAP (carga de facturas) | Si |
| Auditoría y trazabilidad | Si |
| Observabilidad (métricas, alertas) | Si |

### 1.4 Fuera de alcance — Eliminado del sistema anterior

| Módulo eliminado | Motivo |
|---|---|
| Extracción de estados contables | No impacta extracción de facturas ni integración SAP |
| Análisis financiero / ratios | No aplica al pipeline de facturas |
| Generación de reportes contables | Fuera del alcance documental |
| Cualquier módulo no vinculado a facturación o SAP | Limpieza de scope |

---

## Spec 2 — Requerimientos Funcionales

### RF-01: Ingesta de imágenes

- **RF-01.1** — El sistema acepta imágenes en formatos JPEG, PNG, TIFF, PDF (single/multi-page).
- **RF-01.2** — Canales de ingesta:
  - **Mobile**: upload directo vía app o PWA con Signed URL pre-firmada.
  - **Web**: portal de carga con drag & drop.
  - **Bulk**: carga masiva vía Cloud Storage (bucket de ingesta con trigger automático).
- **RF-01.3** — Cada imagen recibe un `document_id` (UUID v4) al momento de ingesta.
- **RF-01.4** — Se registran metadatos: timestamp, canal de origen, usuario, tamaño, hash SHA-256.

### RF-02: Preprocesamiento de imagen

- **RF-02.1** — Deskew automático (corrección de rotación/inclinación).
- **RF-02.2** — Denoise (reducción de ruido para imágenes de baja calidad).
- **RF-02.3** — Ajuste de contraste y binarización adaptativa.
- **RF-02.4** — Detección de bordes y crop automático del área de factura.
- **RF-02.5** — Si la imagen es irrecuperable (resolución <72 DPI, completamente borrosa), se marca como `REJECTED` y se notifica al usuario.

### RF-03: OCR/IDP — Extracción de campos

- **RF-03.1** — Motor principal: **Document AI Invoice Parser** (procesador especializado de Google).
- **RF-03.2** — Campos clave a extraer:

| Campo | Tipo | Obligatorio |
|---|---|---|
| `supplier_name` | string | Si |
| `supplier_cuit` | string (11 dígitos) | Si |
| `invoice_type` | enum (A, B, C, M, E) | Si |
| `invoice_number` | string (punto de venta + nro) | Si |
| `invoice_date` | date (ISO 8601) | Si |
| `due_date` | date | No |
| `currency` | enum (ARS, USD) | Si |
| `net_amount` | decimal | Si |
| `vat_amount` | decimal | Si |
| `total_amount` | decimal | Si |
| `line_items[]` | array of objects | No |
| `cae` | string | Si |
| `cae_due_date` | date | Si |

- **RF-03.3** — Cada campo extraído incluye un `confidence_score` (0.0–1.0).
- **RF-03.4** — Post-procesamiento con **Vertex AI** (modelo custom) para campos que Document AI no cubra o para mejorar accuracy en facturas argentinas.

### RF-04: Validaciones fiscales

- **RF-04.1** — Validación de CUIT: algoritmo módulo 11.
- **RF-04.2** — Validación de consistencia IVA: `net_amount * alícuota ≈ vat_amount` (tolerancia configurable, default ±$1).
- **RF-04.3** — Validación de totales: `net_amount + vat_amount + percepciones ≈ total_amount`.
- **RF-04.4** — Validación de CAE contra AFIP (opcional, vía servicio WSCDC de AFIP).
- **RF-04.5** — Validación de duplicados: misma combinación `supplier_cuit + invoice_type + invoice_number`.

### RF-05: Flujo HITL (Human-In-The-Loop)

- **RF-05.1** — Un documento entra en revisión humana cuando:
  - Algún campo obligatorio tiene `confidence_score < 0.85` (umbral configurable).
  - Falla alguna validación fiscal (RF-04).
  - El documento fue marcado como `REJECTED` en preprocesamiento pero el usuario fuerza la revisión.
- **RF-05.2** — Interfaz de revisión: vista lado a lado (imagen original + campos extraídos editables).
- **RF-05.3** — El revisor puede: aprobar, corregir campos, rechazar documento.
- **RF-05.4** — Las correcciones humanas se almacenan para reentrenamiento futuro del modelo.
- **RF-05.5** — SLA de revisión: configurable por cliente (default: 4 horas laborales).

### RF-06: Integración SAP

- **RF-06.1** — Carga de facturas de proveedor en SAP mediante:
  - **Opción primaria**: SAP OData V2/V4 (API_JOURNALENTRY o BAPI_INCOMINGINVOICE_CREATE).
  - **Opción secundaria**: IDoc (INVOIC02) si el cliente usa ECC sin APIs habilitadas.
  - **Opción terciaria**: RFC vía SAP Cloud Connector si no hay OData ni IDoc.
- **RF-06.2** — Mapeo de campos Triunfo → SAP configurable por cliente (JSON de mapeo).
- **RF-06.3** — Retry con backoff exponencial (max 3 intentos) en caso de fallo transitorio SAP.
- **RF-06.4** — Si la carga falla definitivamente, el documento queda en estado `SAP_ERROR` con detalle del error para intervención manual.
- **RF-06.5** — Confirmación de carga: se almacena el `SAP_DOCUMENT_NUMBER` retornado.

### RF-07: Auditoría y trazabilidad

- **RF-07.1** — Cada documento mantiene un log de eventos inmutable:
  - `INGESTED → PREPROCESSED → EXTRACTED → VALIDATED → [HITL_REVIEW →] SAP_SUBMITTED → SAP_CONFIRMED`
- **RF-07.2** — Cada transición registra: timestamp, actor (sistema/usuario), payload antes/después.
- **RF-07.3** — Retención mínima: 10 años (configurable por regulación).
- **RF-07.4** — La imagen original se preserva sin modificación en bucket de archivo.

---

## Spec 3 — Requerimientos No Funcionales

### RNF-01: Rendimiento

| Métrica | Target | Medición |
|---|---|---|
| Latencia end-to-end (sin HITL) | < 30 segundos por documento | P95 |
| Latencia preprocesamiento | < 5 segundos | P95 |
| Latencia OCR/IDP | < 15 segundos | P95 |
| Throughput sostenido | 500 documentos/hora | Carga continua |
| Throughput pico | 1.500 documentos/hora | Burst de 15 min |
| Tiempo de carga a SAP | < 5 segundos por documento | P95 |

### RNF-02: Calidad

| Métrica | Target |
|---|---|
| Accuracy por campo (imagen buena calidad) | > 97% |
| Accuracy por campo (imagen baja calidad) | > 90% |
| STP rate (sin intervención humana) | > 70% en POC, > 85% en producción |
| Tasa de falsos positivos (campo incorrecto aceptado) | < 1% |

### RNF-03: Seguridad

- **RNF-03.1** — Cifrado en tránsito: TLS 1.3 obligatorio en todos los endpoints.
- **RNF-03.2** — Cifrado en reposo: Google-managed encryption keys (GMEK) mínimo; CMEK para datos sensibles.
- **RNF-03.3** — PII: los datos de proveedores (CUIT, razón social) se consideran PII.
  - Acceso restringido por IAM con principio de menor privilegio.
  - Sin logging de valores PII en texto plano (se loguean hashes o se enmascaran).
- **RNF-03.4** — Autenticación: Identity-Aware Proxy (IAP) para la UI HITL; Service Accounts con Workload Identity para servicios.
- **RNF-03.5** — Red: VPC con Private Google Access; sin IPs públicas en servicios internos.

### RNF-04: Compliance

- **RNF-04.1** — Logs inmutables: Cloud Logging con sink a Cloud Storage (bucket con Object Lock/retention policy).
- **RNF-04.2** — Retención de documentos: 10 años mínimo en Coldline/Archive storage.
- **RNF-04.3** — Trazabilidad: cada acción sobre un documento es auditable (quién, cuándo, qué cambió).
- **RNF-04.4** — Separación de ambientes: dev / staging / prod con proyectos GCP separados.

### RNF-05: Observabilidad

- **RNF-05.1** — Métricas clave exportadas a Cloud Monitoring:
  - `documents_processed_total` (counter por estado final)
  - `processing_latency_seconds` (histogram por etapa)
  - `ocr_confidence_score` (histogram por campo)
  - `stp_rate` (gauge)
  - `sap_integration_errors_total` (counter por tipo de error)
- **RNF-05.2** — Alertas:
  - STP rate < umbral durante 30 min → alerta a Ops.
  - Error rate SAP > 5% en ventana de 10 min → alerta crítica.
  - Cola HITL > 100 documentos pendientes → alerta a supervisores.
- **RNF-05.3** — Dashboard operativo en Cloud Monitoring (o Looker Studio) con vista en tiempo real.
- **RNF-05.4** — Tracing distribuido con Cloud Trace para correlacionar latencia por etapa.

---

## Spec 4 — Arquitectura Técnica en GCP

### 4.1 Diagrama de componentes (textual)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            INGESTA                                      │
│  Mobile/Web ──► Cloud Storage (bucket-ingesta) ◄── Bulk upload          │
│                    │ Signed URLs via API Gateway                         │
│                    ▼                                                     │
│              Pub/Sub (topic: doc-ingested)                               │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PREPROCESAMIENTO                                  │
│  Cloud Run (servicio: preprocessor)                                     │
│  - OpenCV: deskew, denoise, contraste, crop                             │
│  - Valida calidad mínima (DPI, blur detection)                          │
│  - Escribe imagen procesada en bucket-processed                         │
│              │                                                          │
│              ▼                                                          │
│        Pub/Sub (topic: doc-preprocessed)                                │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        OCR / IDP                                        │
│  Cloud Run (servicio: extractor)                                        │
│  - Llama a Document AI Invoice Parser (API)                             │
│  - Post-procesamiento con Vertex AI (campos AR-específicos)             │
│  - Genera JSON estructurado con campos + confidence                     │
│              │                                                          │
│              ▼                                                          │
│        Pub/Sub (topic: doc-extracted)                                   │
└────────────────────┬────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   VALIDACIÓN + ROUTING                                  │
│  Cloud Run (servicio: validator)                                        │
│  - Validaciones fiscales (CUIT, IVA, totales, duplicados)               │
│  - Evalúa confidence scores vs umbral                                   │
│  - Routing:                                                             │
│      confidence OK + validación OK  ──► Pub/Sub (topic: doc-approved)   │
│      confidence LOW o validación FAIL ► Pub/Sub (topic: doc-hitl)       │
└───────────┬──────────────────────────────────┬──────────────────────────┘
            ▼                                  ▼
┌───────────────────────┐      ┌──────────────────────────────────────────┐
│    INTEGRACIÓN SAP    │      │              HITL                        │
│  Cloud Run (sap-loader)│      │  Cloud Run (hitl-ui) + Firestore        │
│  - OData / IDoc / RFC │      │  - UI revisión lado a lado              │
│  - Retry + circuit    │      │  - Corrección de campos                 │
│    breaker            │      │  - Aprobación / Rechazo                 │
│  - Almacena SAP doc # │      │  - Correcciones → doc-approved          │
│  - Cloud SQL (estado) │      │       o → doc-rejected                  │
└───────────────────────┘      └──────────────────────────────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       DATOS Y AUDITORÍA                                 │
│  Cloud SQL (PostgreSQL) — estado de documentos, mapeos, configuración   │
│  Firestore — cola HITL, sesiones de revisión                            │
│  Cloud Storage — imágenes originales (Archive), procesadas (Standard)   │
│  Cloud Logging — logs inmutables → sink a bucket con retention policy   │
│  Cloud Monitoring + Cloud Trace — métricas, alertas, tracing            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Decisiones técnicas explícitas

| Decisión | Elegido | Descartado | Motivo |
|---|---|---|---|
| Orquestación | **Pub/Sub + Cloud Run** | Cloud Functions, Workflows | Cloud Run da más control sobre timeouts, concurrencia y tamaño de contenedor (OpenCV necesita ~512MB imagen). Pub/Sub desacopla etapas y permite retry nativo. |
| Preprocesamiento | **Cloud Run con OpenCV** | Dataflow | Dataflow tiene overhead de startup (~2 min) inaceptable para latencia <5s. Cloud Run con min-instances=1 resuelve cold start. |
| OCR/IDP | **Document AI Invoice Parser** | Cloud Vision OCR genérico, Tesseract | Invoice Parser es un modelo especializado en facturas con extracción de campos estructurados. Vision OCR es genérico (solo texto). Tesseract requiere infra propia y menor accuracy. |
| Post-procesamiento ML | **Vertex AI (endpoint custom)** | Solo Document AI | Document AI no cubre campos AR-específicos (CAE, tipo factura AFIP). Vertex AI permite fine-tune. |
| Base de datos operativa | **Cloud SQL (PostgreSQL)** | Firestore, Spanner | Necesitamos queries relacionales (joins para duplicados, reportes). Spanner es overkill para este volumen. |
| Cola HITL | **Firestore** | Cloud SQL | Firestore ofrece real-time listeners para la UI sin WebSockets custom. Modelo documental encaja con la cola de revisión. |
| Almacenamiento imágenes | **Cloud Storage (multi-tier)** | Filestore | Cloud Storage con lifecycle policies (Standard → Nearline → Archive) optimiza costos a 10 años. |
| Integración SAP | **Cloud Run + SAP Cloud Connector** | SAP Integration Suite (CPI) | CPI agrega costo de licencia. Cloud Run con SDK OData/RFC es suficiente y mantiene todo en GCP. Se puede migrar a CPI si el cliente lo requiere. |
| API Gateway | **API Gateway (GCP)** | Apigee | Apigee es enterprise overkill para este volumen. API Gateway cubre rate limiting, auth y Signed URLs. |
| IaC | **Terraform** | Pulumi, Deployment Manager | Estándar de industria, soporte maduro para todos los servicios GCP usados. |
| CI/CD | **Cloud Build** | GitHub Actions, Jenkins | Nativo GCP, integración directa con Artifact Registry y Cloud Run. |
| Lenguaje backend | **Python 3.12** | Go, Node.js | Ecosistema ML/CV (OpenCV, Document AI SDK, Vertex AI SDK) es Python-first. Cloud Run no impone restricción de lenguaje. |
| Contenedores | **Artifact Registry** | Container Registry (deprecated) | Container Registry está deprecated en GCP. Artifact Registry es el reemplazo oficial. |

### 4.3 Flujo de datos y eventos

```
Evento Pub/Sub          Productor          Consumidor         Payload clave
─────────────────────────────────────────────────────────────────────────────
doc-ingested            Storage trigger    preprocessor       {document_id, gcs_uri, metadata}
doc-preprocessed        preprocessor       extractor          {document_id, processed_gcs_uri, quality_score}
doc-extracted           extractor          validator          {document_id, fields{}, confidences{}}
doc-approved            validator / HITL   sap-loader         {document_id, validated_fields{}}
doc-hitl                validator          hitl-ui            {document_id, fields{}, issues[]}
doc-rejected            HITL               (terminal)         {document_id, reason, reviewer}
doc-sap-confirmed       sap-loader         (terminal)         {document_id, sap_doc_number}
doc-sap-error           sap-loader         (alerting)         {document_id, error_detail, attempt}
```

### 4.4 Infraestructura

- **Región**: `southamerica-east1` (São Paulo) — menor latencia desde Argentina, Document AI disponible.
- **Ambientes**: 3 proyectos GCP (`triunfo-dev`, `triunfo-staging`, `triunfo-prod`).
- **Networking**: VPC compartida, Private Google Access, Cloud NAT para egress a SAP on-prem.
- **SAP Connectivity**: Cloud VPN o Interconnect hacia la red SAP del cliente + SAP Cloud Connector.

---

## Spec 5 — Contratos de Datos

### 5.1 Esquema de entrada (metadatos de ingesta)

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_channel": "mobile",
  "uploaded_by": "user@empresa.com",
  "uploaded_at": "2026-04-10T15:30:00Z",
  "original_filename": "factura_001.jpg",
  "mime_type": "image/jpeg",
  "file_size_bytes": 2048576,
  "sha256_hash": "a3f2b8c1d4e5f6...",
  "gcs_uri": "gs://triunfo-prod-ingesta/2026/04/10/550e8400.jpg",
  "client_id": "cliente-abc",
  "metadata": {
    "device": "iPhone 14",
    "gps_lat": null,
    "gps_lon": null
  }
}
```

### 5.2 Esquema de salida (resultado de extracción + validación)

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "VALIDATED",
  "processing_timestamp": "2026-04-10T15:30:28Z",
  "extraction": {
    "supplier_name": {
      "value": "Distribuidora Norte S.A.",
      "confidence": 0.97
    },
    "supplier_cuit": {
      "value": "30-71234567-9",
      "confidence": 0.99
    },
    "invoice_type": {
      "value": "A",
      "confidence": 0.98
    },
    "invoice_number": {
      "value": "0003-00012345",
      "confidence": 0.96
    },
    "invoice_date": {
      "value": "2026-03-15",
      "confidence": 0.99
    },
    "due_date": {
      "value": "2026-04-15",
      "confidence": 0.92
    },
    "currency": {
      "value": "ARS",
      "confidence": 0.99
    },
    "net_amount": {
      "value": 150000.00,
      "confidence": 0.95
    },
    "vat_amount": {
      "value": 31500.00,
      "confidence": 0.95
    },
    "total_amount": {
      "value": 181500.00,
      "confidence": 0.97
    },
    "cae": {
      "value": "73241567890123",
      "confidence": 0.94
    },
    "cae_due_date": {
      "value": "2026-03-25",
      "confidence": 0.93
    },
    "line_items": [
      {
        "description": {"value": "Producto A x100", "confidence": 0.88},
        "quantity": {"value": 100, "confidence": 0.91},
        "unit_price": {"value": 1500.00, "confidence": 0.90},
        "subtotal": {"value": 150000.00, "confidence": 0.92}
      }
    ]
  },
  "validation": {
    "cuit_valid": true,
    "vat_consistent": true,
    "totals_consistent": true,
    "duplicate_check": false,
    "cae_valid": null,
    "errors": []
  },
  "quality": {
    "image_dpi": 150,
    "blur_score": 0.12,
    "preprocessing_applied": ["deskew", "contrast"]
  }
}
```

### 5.3 Mapeo a SAP — Ejemplo de payload

#### Opción A: OData — BAPI_INCOMINGINVOICE_CREATE (simulado como JSON)

```json
{
  "HEADERDATA": {
    "INVOICE_IND": "X",
    "DOC_TYPE": "RE",
    "DOC_DATE": "20260315",
    "PSTNG_DATE": "20260410",
    "REF_DOC_NO": "0003-00012345",
    "COMP_CODE": "1000",
    "CURRENCY": "ARS",
    "GROSS_AMOUNT": 181500.00,
    "CALC_TAX_IND": "",
    "BUS_ACT": "MRRL"
  },
  "ADDRESSDATA": {
    "NAME": "Distribuidora Norte S.A.",
    "TAX_NO_1": "30712345679"
  },
  "ITEMDATA": [
    {
      "INVOICE_DOC_ITEM": "0001",
      "PO_NUMBER": "",
      "PO_ITEM": "",
      "TAX_CODE": "I1",
      "ITEM_AMOUNT": 150000.00,
      "GL_ACCOUNT": "4000000",
      "COSTCENTER": ""
    }
  ],
  "TAXDATA": [
    {
      "TAX_CODE": "I1",
      "TAX_AMOUNT": 31500.00
    }
  ]
}
```

#### Tabla de mapeo Triunfo → SAP

| Campo Triunfo | Campo SAP | Transformación |
|---|---|---|
| `invoice_date` | `HEADERDATA.DOC_DATE` | Formato `YYYYMMDD` |
| `invoice_number` | `HEADERDATA.REF_DOC_NO` | Directo |
| `currency` | `HEADERDATA.CURRENCY` | Directo |
| `total_amount` | `HEADERDATA.GROSS_AMOUNT` | Directo |
| `supplier_cuit` | `ADDRESSDATA.TAX_NO_1` | Sin guiones |
| `supplier_name` | `ADDRESSDATA.NAME` | Directo |
| `net_amount` | `ITEMDATA[].ITEM_AMOUNT` | Por línea o agregado |
| `vat_amount` | `TAXDATA[].TAX_AMOUNT` | Por alícuota |
| `invoice_type` | Determina `TAX_CODE` | Lógica configurable (A→I1, B→I5, etc.) |

> **Nota**: El mapeo exacto depende de la customización SAP del cliente. La tabla es configurable vía JSON en Cloud SQL.

---

## Spec 6 — Roadmap Técnico por Fases

### Fase 1: POC (6 semanas)

**Objetivo**: Demostrar viabilidad técnica del pipeline completo con un set reducido de facturas.

| Entregable | Detalle |
|---|---|
| Pipeline mínimo | Ingesta → Document AI → Validación → Log (sin SAP real) |
| Golden set | 100 facturas anotadas manualmente (ground truth) |
| Métricas de accuracy | Report por campo sobre el golden set |
| Mock SAP | Endpoint simulado que valida el payload OData |
| Infra base | Terraform para un solo ambiente (dev) |

**Criterios de salida**:
- Accuracy por campo > 90% en el golden set.
- Pipeline end-to-end ejecuta sin errores en 80% de los documentos.
- Latencia < 45 segundos P95.

**Riesgos de fase**:
- Document AI no cubre campos AR-específicos → Mitigación: validar al día 5 con 20 facturas reales.
- Calidad de imágenes del golden set no es representativa → Mitigación: incluir al menos 30% imágenes de baja calidad.

---

### Fase 2: Piloto (8 semanas)

**Objetivo**: Operar con usuarios reales, integración SAP real, flujo HITL funcional.

| Entregable | Detalle |
|---|---|
| Integración SAP real | Conexión a sandbox SAP del cliente; carga real de facturas |
| UI HITL | Interfaz de revisión humana funcional |
| Preprocesamiento | Pipeline completo de mejora de imagen |
| Vertex AI fine-tune | Modelo custom entrenado con correcciones HITL de la POC |
| Observabilidad | Dashboard operativo + alertas básicas |
| Infra staging | Ambiente staging con IaC completo |

**Criterios de salida**:
- STP rate > 70% con facturas reales del cliente.
- Accuracy > 95% en campos obligatorios.
- Integración SAP exitosa en > 90% de facturas aprobadas.
- Flujo HITL probado con al menos 3 revisores reales.
- Latencia < 30 segundos P95 sin HITL.

**Riesgos de fase**:
- SAP sandbox difiere de producción → Mitigación: validar con equipo SAP del cliente en semana 1.
- Volumen de HITL demasiado alto → Mitigación: ajustar umbrales de confianza iterativamente.

---

### Fase 3: Producción (6 semanas)

**Objetivo**: Go-live con volumen real, SLA comprometidos, operación continua.

| Entregable | Detalle |
|---|---|
| Hardening | Rate limiting, circuit breakers, retry policies |
| Seguridad | IAP, CMEK, auditoría de accesos |
| IaC producción | Proyecto prod con networking, VPN a SAP |
| Runbooks | Procedimientos operativos documentados |
| Capacitación | Training a usuarios HITL y operadores |
| Métricas de negocio | Dashboard ejecutivo (STP rate, ahorro de tiempo) |

**Criterios de salida**:
- STP rate > 80%.
- Uptime > 99.5% en ventana de 30 días.
- Cero pérdida de documentos.
- Auditoría de seguridad aprobada.
- Todos los runbooks probados en simulacro.

**Métricas de éxito globales**:

| Métrica | Target producción |
|---|---|
| STP rate | > 85% en mes 3 post go-live |
| Accuracy campos obligatorios | > 97% |
| Tiempo promedio de procesamiento | < 30 seg (sin HITL) |
| Reducción de carga manual | > 70% vs baseline |
| Satisfacción usuarios HITL | > 4/5 en encuesta |

**Pruebas**:
- **Golden set**: 500 facturas anotadas; ejecutar en cada release.
- **A/B OCR**: comparar Document AI vs Document AI + Vertex AI post-processing; medir delta de accuracy.
- **Pruebas de carga**: simular throughput pico (1.500 doc/hora) durante 1 hora.
- **Prueba de failover**: simular caída de SAP; verificar que los documentos quedan en cola y se procesan al restaurar.

---

## Spec 7 — Backlog Inicial

### Epic 1: Ingesta de documentos

| ID | User Story | Prioridad |
|---|---|---|
| US-101 | Como usuario mobile, quiero sacar una foto de una factura y que se suba automáticamente al sistema | Must |
| US-102 | Como usuario web, quiero subir una o varias facturas mediante drag & drop | Must |
| US-103 | Como operador, quiero cargar un batch de facturas desde una carpeta compartida | Should |
| US-104 | Como sistema, debo generar un document_id único y registrar metadatos al recibir cada imagen | Must |

### Epic 2: Preprocesamiento de imagen

| ID | User Story | Prioridad |
|---|---|---|
| US-201 | Como sistema, debo corregir la rotación e inclinación de la imagen automáticamente | Must |
| US-202 | Como sistema, debo mejorar el contraste y reducir ruido en imágenes de baja calidad | Must |
| US-203 | Como sistema, debo rechazar imágenes irrecuperables y notificar al usuario | Should |
| US-204 | Como sistema, debo registrar un quality_score por cada imagen procesada | Should |

### Epic 3: OCR/IDP y extracción

| ID | User Story | Prioridad |
|---|---|---|
| US-301 | Como sistema, debo extraer todos los campos obligatorios de una factura usando Document AI | Must |
| US-302 | Como sistema, debo asignar un confidence_score a cada campo extraído | Must |
| US-303 | Como sistema, debo usar Vertex AI para mejorar la extracción de campos AR-específicos (CAE, tipo factura) | Should |
| US-304 | Como sistema, debo soportar facturas multi-page (PDF) | Should |

### Epic 4: Validaciones fiscales

| ID | User Story | Prioridad |
|---|---|---|
| US-401 | Como sistema, debo validar el CUIT del proveedor (algoritmo módulo 11) | Must |
| US-402 | Como sistema, debo validar la consistencia entre neto, IVA y total | Must |
| US-403 | Como sistema, debo detectar facturas duplicadas (CUIT + tipo + número) | Must |
| US-404 | Como sistema, debo validar el CAE contra AFIP (opcional) | Could |

### Epic 5: Flujo HITL

| ID | User Story | Prioridad |
|---|---|---|
| US-501 | Como revisor, quiero ver la imagen de la factura junto a los campos extraídos para poder corregirlos | Must |
| US-502 | Como revisor, quiero aprobar o rechazar una factura con un click | Must |
| US-503 | Como supervisor, quiero ver la cola de facturas pendientes de revisión y su antigüedad | Should |
| US-504 | Como sistema, debo almacenar las correcciones humanas para futuro reentrenamiento | Should |

### Epic 6: Integración SAP

| ID | User Story | Prioridad |
|---|---|---|
| US-601 | Como sistema, debo cargar una factura validada en SAP mediante OData/IDoc | Must |
| US-602 | Como sistema, debo reintentar la carga a SAP automáticamente ante fallas transitorias | Must |
| US-603 | Como operador, quiero ver qué facturas fallaron al cargar en SAP y el motivo | Must |
| US-604 | Como administrador, quiero configurar el mapeo de campos Triunfo → SAP sin tocar código | Should |

### Epic 7: Auditoría y observabilidad

| ID | User Story | Prioridad |
|---|---|---|
| US-701 | Como auditor, quiero consultar el historial completo de un documento desde ingesta hasta SAP | Must |
| US-702 | Como operador, quiero un dashboard con métricas en tiempo real (STP rate, errores, cola HITL) | Should |
| US-703 | Como operador, quiero recibir alertas cuando el STP rate baje del umbral | Should |
| US-704 | Como compliance, quiero que los logs sean inmutables y retenidos por 10 años | Must |

### Epic 8: Infraestructura y DevOps

| ID | User Story | Prioridad |
|---|---|---|
| US-801 | Como DevOps, quiero toda la infraestructura definida en Terraform | Must |
| US-802 | Como DevOps, quiero un pipeline CI/CD con Cloud Build que ejecute tests y deploys | Must |
| US-803 | Como DevOps, quiero ambientes separados (dev/staging/prod) con promoción controlada | Should |

---

## Spec 8 — Riesgos y Mitigaciones

### R-01: Calidad de imagen

| | Detalle |
|---|---|
| **Riesgo** | Las fotos de facturas tomadas desde móvil tienen baja resolución, desenfoque, sombras o reflejos que degradan la extracción |
| **Probabilidad** | Alta |
| **Impacto** | Alto — reduce STP rate y aumenta carga HITL |
| **Mitigación** | (1) Pipeline de preprocesamiento robusto (deskew, denoise, contraste). (2) Guía UX en la app mobile (overlay de encuadre, detección de blur antes de upload). (3) Golden set con 30%+ imágenes de baja calidad para medir accuracy real. (4) Threshold de rechazo configurable para evitar procesar basura |

### R-02: Sesgos y limitaciones del OCR

| | Detalle |
|---|---|
| **Riesgo** | Document AI está entrenado mayormente con facturas internacionales; los formatos argentinos (tipo A/B/C, CAE, punto de venta) podrían tener menor accuracy |
| **Probabilidad** | Media-Alta |
| **Impacto** | Alto — campos AR-específicos son obligatorios |
| **Mitigación** | (1) Evaluar en POC día 5 con 20 facturas reales argentinas. (2) Vertex AI fine-tune con dataset local. (3) Reglas de post-procesamiento para normalizar formatos AR (regex para CAE, CUIT, punto de venta). (4) Feedback loop desde HITL para reentrenamiento continuo |

### R-03: Costos GCP

| | Detalle |
|---|---|
| **Riesgo** | Document AI cobra por página ($0.065 en Invoice Parser). A volumen alto, el costo puede ser significativo |
| **Probabilidad** | Media |
| **Impacto** | Medio — impacta viabilidad económica |
| **Mitigación** | (1) Calcular costo unitario en POC y comparar contra costo de carga manual. (2) Negociar committed use discounts con Google. (3) Pre-filtrar imágenes irrecuperables antes de enviar a Document AI. (4) Monitorear costo por documento con billing alerts |

### R-04: Fallas de integración SAP

| | Detalle |
|---|---|
| **Riesgo** | SAP on-prem puede tener indisponibilidad, configuración custom, o rechazar payloads por validaciones propias |
| **Probabilidad** | Alta |
| **Impacto** | Alto — sin SAP no hay valor de negocio |
| **Mitigación** | (1) Cola de retry con dead-letter topic en Pub/Sub. (2) Circuit breaker para no saturar SAP. (3) Validar en sandbox SAP del cliente desde semana 1 de Piloto. (4) Mapeo configurable para adaptarse a customizaciones. (5) Modo offline: acumular y procesar cuando SAP se recupere |

### R-05: Seguridad y compliance

| | Detalle |
|---|---|
| **Riesgo** | Datos fiscales (CUIT, montos) son sensibles. Una brecha expone datos de proveedores |
| **Probabilidad** | Baja |
| **Impacto** | Crítico |
| **Mitigación** | (1) CMEK en buckets con datos sensibles. (2) IAM con menor privilegio. (3) VPC sin IPs públicas. (4) Auditoría de accesos con Cloud Audit Logs. (5) Penetration test antes de go-live |

### R-06: Dependencia de un único proveedor OCR

| | Detalle |
|---|---|
| **Riesgo** | Si Document AI cambia precios, degrada calidad o depreca el Invoice Parser, no hay alternativa inmediata |
| **Probabilidad** | Baja |
| **Impacto** | Alto |
| **Mitigación** | (1) Abstraer la capa OCR detrás de una interfaz (strategy pattern) para poder reemplazar el motor. (2) Medir accuracy en cada release contra golden set para detectar degradación temprano |

### R-07: Adopción por usuarios

| | Detalle |
|---|---|
| **Riesgo** | Los revisores HITL o usuarios de carga no adoptan el sistema; vuelven al proceso manual |
| **Probabilidad** | Media |
| **Impacto** | Alto — sin adopción no hay ROI |
| **Mitigación** | (1) UX simple y rápida (< 3 clicks para revisar un documento). (2) Capacitación en Fase 3. (3) Medir satisfacción y ajustar iterativamente. (4) Mostrar métricas de ahorro de tiempo para motivar uso |

---

## Spec 9 — Preguntas Abiertas

### Sobre SAP

| # | Pregunta | Impacta a |
|---|---|---|
| PA-01 | **¿SAP ECC o S/4HANA?** Define la API disponible (BAPI vs OData nativo) | RF-06, Arquitectura |
| PA-02 | ¿Qué versión específica? ¿Tiene SAP Gateway habilitado? | RF-06 |
| PA-03 | ¿Existe SAP Cloud Connector o se debe instalar? | Infra, networking |
| PA-04 | ¿Qué transacción se usa hoy para cargar facturas manualmente? (MIRO, FB60, otra) | Mapeo SAP |
| PA-05 | ¿Hay customizaciones relevantes en el módulo FI/MM? (campos Z, validaciones custom) | Contrato de datos |
| PA-06 | ¿Se requiere matching con orden de compra (PO) o es carga libre? | RF-06, complejidad |

### Sobre volumen y operación

| # | Pregunta | Impacta a |
|---|---|---|
| PA-07 | ¿Volumen diario estimado de facturas? (unidades por día) | Sizing, costos GCP |
| PA-08 | ¿Hay picos estacionales? (ej: cierre de mes, fin de año fiscal) | Auto-scaling |
| PA-09 | ¿Cuántos revisores HITL habrá disponibles? | Diseño de cola, SLA |
| PA-10 | ¿Horario de operación? ¿24x7 o solo horario laboral? | SLA, costos |

### Sobre documentos

| # | Pregunta | Impacta a |
|---|---|---|
| PA-11 | ¿Qué tipos de factura se procesan? (A, B, C, M, E, notas de crédito/débito) | RF-03, validaciones |
| PA-12 | ¿Las facturas son solo de proveedores nacionales o también del exterior? | Validaciones, campos |
| PA-13 | ¿Hay facturas electrónicas (PDF de AFIP) o solo fotos de papel? | Preprocesamiento |
| PA-14 | ¿Calidad esperada de imágenes? ¿Se toman con celular en condiciones controladas o en campo? | RNF-02, preprocesamiento |
| PA-15 | ¿Se necesita extraer line items o solo los totales? | Complejidad de extracción |

### Sobre integración y seguridad

| # | Pregunta | Impacta a |
|---|---|---|
| PA-16 | ¿Existe un sistema de autenticación corporativo (SSO/SAML/OIDC) para la UI? | RNF-03, IAP |
| PA-17 | ¿Hay requisitos de residencia de datos? (¿los datos deben quedarse en Argentina?) | Región GCP |
| PA-18 | ¿Se requiere integración con algún otro sistema además de SAP? (ERP, DMS, etc.) | Alcance |
| PA-19 | ¿Quién es el equipo de operaciones? ¿Hay capacidad DevOps interna? | Runbooks, soporte |

---

## Apéndice A — Estimación de costos GCP (orden de magnitud)

> Basado en 500 documentos/día, ~15.000/mes.

| Servicio | Estimación mensual (USD) |
|---|---|
| Document AI Invoice Parser (15K páginas) | ~$975 |
| Cloud Run (5 servicios, ~2 vCPU promedio) | ~$300 |
| Cloud SQL (PostgreSQL, db-standard-2) | ~$150 |
| Cloud Storage (ingesta + archivo) | ~$50 |
| Pub/Sub | ~$20 |
| Vertex AI (endpoint online, uso moderado) | ~$200 |
| Cloud Monitoring + Logging | ~$100 |
| Networking (egress, VPN) | ~$50 |
| **Total estimado** | **~$1.845/mes** |

> Estos valores son orientativos y dependen del volumen real (PA-07). El costo dominante es Document AI; negociar committed use es crítico.

---

## Apéndice B — Glosario

| Término | Definición |
|---|---|
| STP | Straight-Through Processing — documento procesado sin intervención humana |
| HITL | Human-In-The-Loop — revisión humana de documentos con baja confianza |
| IDP | Intelligent Document Processing — extracción estructurada de documentos |
| CAE | Código de Autorización Electrónico (AFIP) |
| CUIT | Clave Única de Identificación Tributaria |
| IDoc | Intermediate Document — formato de intercambio de SAP |
| BAPI | Business Application Programming Interface — API funcional de SAP |
| OData | Open Data Protocol — API REST estándar de SAP |
| CMEK | Customer-Managed Encryption Keys |
| IAP | Identity-Aware Proxy (GCP) |
