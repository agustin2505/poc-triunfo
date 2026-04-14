# Triunfo — Spec-09 UI Demo v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Páginas principales

### 1. Upload & Processing
- Drag-drop o file picker (JPEG, PNG)
- Preview de imagen cargada
- Spinner con estado en tiempo real
- Estados: INGESTED -> CLASSIFIED -> PROCESSING -> VALIDATED -> ROUTED

### 2. Resultados (después de procesamiento)

#### Panel A: Datos Extraídos (tabla principal)
Mostrar tabla con:
| Campo | Valor Extraído | Confidence | Fuente | Agente A | Agente B | Agente C |
|-------|--------|-----------|--------|----------|----------|----------|
| provider_name | Edenor | 0.96 | majority | 0.96 | 0.88 | 0.94 |
| issue_date | 2026-03-01 | 0.90 | majority | 0.90 | 0.92 | 0.88 |
| total_amount | 12345.67 | 0.94 | majority | 0.94 | 0.93 | 0.94 |
| reference_number | 0001-00012345 | 0.88 | majority | 0.88 | N/A | 0.88 |

Funcionalidad: clickear en fila para ver detalle de cada agente

#### Panel B: Métricas de Modelos
Card con estadísticas:
- Modelos utilizados: DocumentAI, Tesseract
- Modelos skipped: Vertex (N/A - rendimiento ok con A+B)
- Duración por etapa:
  - Clasificación: 800ms
  - DocumentAI: 1200ms
  - Tesseract: 400ms
  - Validación: 250ms
  - Conciliación: 150ms
- Duración total: 3.4 segundos
- Confidence global: 0.92

#### Panel C: Validaciones
- Estado: PASSED / WARNINGS / FAILED
- Listado de warnings/errores
- Campo missing: due_date, period_start
- Reglas aplicadas: Edenor-specific

#### Panel D: Routing Decision
- Estado: AUTO_APPROVE / HITL_STANDARD / HITL_PRIORITY / AUTO_REJECT
- Razón del routing
- Acciones disponibles según estado

### 3. Detalle por Agente (modal)
Click en agente → mostrar:
- Raw OCR/extracción
- Confidence por campo
- Duración
- Status (SUCCESS/TIMEOUT/FAILED)
- Modelo version

### 4. Log de Cambios (si hay HITL)
Tabla de auditoría:
- Timestamp
- Usuario
- Campo
- Valor anterior
- Valor nuevo
- Razón (comentario)

## Funcionalidades interactivas

1. Upload: drag-drop + file picker
2. View Raw Image: expandir preview
3. Edit Fields (si HITL): editar valor + guardar
4. Approve: enviar a SAP mock (si AUTO_APPROVE)
5. Request Manual Review: cambiar a HITL
6. Download Report: JSON con todos los datos
7. Refresh: recargar estado
8. Back: nueva carga

## Responsive
- Desktop: layout de 2 columnas (imagen + resultados)
- Mobile: tabs (Imagen, Datos, Métricas, Validaciones)
