# Triunfo MVP — Sistema OCR/IDP de Facturas

Demo funcional de un pipeline de OCR/IDP para facturas (imágenes y PDFs) con múltiples agentes, conciliación por mayoría, validaciones y routing automático, además de UI y API FastAPI.

## ✨ Características

- **Múltiples formatos**: Imágenes (JPEG, PNG) + PDFs (texto seleccionable o escaneados)
- **5 agentes especializados**:
  - Agente D: Clasificador de proveedor/categoría (keywords)
  - Agente A: Document AI mock
  - Agente B: Tesseract + regex (OCR local)
  - Agente C: Vertex AI mock (fallback)
  - Agente E: Validador/normalizador
- **Conciliación inteligente**: Mayoría para strings, promedio ponderado para numéricos, fuzzy matching
- **Validaciones**: Genéricas (montos, fechas, duplicados) + específicas por proveedor (Edenor, Metrogas, Factura Interna)
- **Routing automático**: AUTO_APPROVE → SAP, HITL, AUTO_REJECT
- **Descargas**: JSON + PDF formateado con resultados
- **UI demo**: 4 paneles con outputs de agentes, métricas, validaciones y decisión

## Quick Start

### 1. Instalar dependencias

```bash
cd D:\poc-triunfo
pip install -r requirements.txt
```

### 2. Arrancar el servidor

```bash
python run.py
```

Accesible en:
- **UI**: http://localhost:8000/app
- **API Docs**: http://localhost:8000/docs

### 3. Usar la UI

1. **Upload**: Arrastra un archivo (imagen o PDF) o clickea para seleccionar
2. **Opciones**:
   - Proveedor (auto-detecta o fuerza uno)
   - Calidad (good/medium/poor para demo)
3. **Resultados**: 4 paneles:
   - **Panel A**: Datos extraídos por cada agente + confidence
   - **Panel B**: Métricas (timeline, modelos usados, duración)
   - **Panel C**: Validaciones (errores, warnings)
   - **Panel D**: Decisión de routing + botones de acción

4. **Descargar**:
   - JSON con datos completos
   - PDF formateado con resultados

## Ejemplos de uso

### Subir imagen (cURL)

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@factura.jpg" \
  -F "provider_hint=edenor-001" \
  -F "quality_hint=good"
```

### Subir PDF (cURL)

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@factura.pdf" \
  -F "provider_hint=metrogas-001"
```

### Descargar PDF de resultados

```bash
curl http://localhost:8000/document/{document_id}/pdf \
  -o resultado.pdf
```

## Tests

```bash
python -m pytest tests/ -v
# 50 tests: validaciones, conciliación, pipeline end-to-end
```

## Estructura

```
api/                 # FastAPI + endpoints
frontend/            # HTML/JS UI
scripts/             # utilidades (golden set)
src/
├── agents/          # 5 agentes (A, B, C, D, E)
├── conciliation/    # Algoritmo de mayoría
├── config/          # Catálogo de proveedores + sede
├── models/          # Contratos Pydantic
├── pipeline/        # Orquestación
├── sap/             # SAP mock
├── validation/      # Validaciones genéricas + específicas
├── pdf_handler.py   # Lectura de PDFs
└── pdf_generator.py # Generación de reportes PDF
tests/               # pytest (pipeline, validaciones, conciliación)
```

## Flujo del pipeline

1. **Clasificación** (Agente D)
2. **Extracción** en paralelo (Agentes A + B)
3. **Fallback** (Agente C si A+B fallan)
4. **Normalización** (Agente E)
5. **Conciliación** por mayoría
6. **Validaciones** genéricas + por proveedor
7. **Routing** final

## Configuración

### Proveedores soportados (MVP)
- **Edenor** (Electricidad): campos de consumo, medidor, tarifa
- **Metrogas** (Gas): campos de consumo, moneda
- **Factura Interna** (Negocio): items, subtotal, impuestos

### Sedes configuradas
- **demo-001**: Buenos Aires, ARS, AR_CONSUMER

## Routing

| Score | Acción |
|-------|--------|
| >= 0.88 | AUTO_APPROVE → envío automático a SAP |
| 0.70-0.88 | HITL_STANDARD → revisión manual |
| < 0.70 | HITL_PRIORITY → revisión prioritaria |
| < 0.40 | AUTO_REJECT |

## Credenciales

**No requiere credenciales GCP para el demo** — todos los servicios (Document AI, Vertex AI, GCS) están mockeados.

Para producción:
- `GOOGLE_APPLICATION_CREDENTIALS`: path a JSON de service account
- Cloud SQL connection string
- Tesseract binary: `choco install tesseract` (Windows)

## API

Principales endpoints:

- `GET /health` — health check
- `POST /upload` — procesa imagen o PDF
- `GET /document/{document_id}` — resultado completo
- `POST /document/{document_id}/approve` — envía a SAP mock
- `GET /document/{document_id}/pdf` — PDF con resultados
- `GET /documents` — lista de documentos
- `DELETE /documents/reset` — limpia estado (demo)
- `GET /providers` — catálogo de proveedores

## Spec Referencias

Todas las especificaciones se encuentran en `docs/specs-mvp/`:
- spec-01: Alcance MVP
- spec-02: Agentes
- spec-03: Contratos datos
- spec-04: Conciliación
- spec-05: Validaciones
- spec-06: Catálogo proveedores
- spec-07: Configuración sede
- spec-08: SAP mock
- spec-09: UI demo
- spec-10: Data seeding
- spec-11: Testing plan
- spec-12: Monitoring & logs

## Roadmap

- [x] MVP con 3 proveedores
- [x] 5 agentes funcionando
- [x] Conciliación multi-agente
- [x] Validaciones genéricas + específicas
- [x] SAP mock
- [x] UI demo (4 paneles)
- [x] Descargas (JSON + PDF)
- [x] 50 tests
- [ ] HITL review UI
- [ ] Cloud SQL persistencia
- [ ] Tesseract OCR real
- [ ] Document AI real
- [ ] Cloud Logging
- [ ] Multi-sede en operación

## Soporte

- **Issues**: Ver `docs/specs-mvp/`
- **Logs**: stdout (modo dev) / Cloud Logging (prod)

---

**Generado**: 2026-04-14 | **MVP v1.0** | Triunfo 🚀
