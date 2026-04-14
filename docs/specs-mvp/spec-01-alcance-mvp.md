# Triunfo — Spec-01 Alcance MVP v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Objetivo
Demo funcional end-to-end del pipeline con 5 agentes, conciliación por mayoría + reglas específicas, validaciones por proveedor, y UI con métricas de modelos.

## Alcance funcional
- 1 sede: demo-001 (Argentina, ARS, AR_CONSUMER)
- 3 proveedores: Edenor, Metrogas, Factura Interna
- Ingesta web (upload + preview)
- Clasificación automática (categoría + proveedor)
- Extracción multi-agente con fallback chain
- Conciliación (mayoría simple + reglas numéricas)
- Validaciones genéricas + específicas por proveedor
- Enrutamiento (AUTO_APPROVE / HITL_STANDARD / HITL_PRIORITY)
- SAP mock con auditoría
- UI con: resultados por agente, conciliación visual, datos extraídos, métricas de modelos

## Métricas de éxito (MVP)
- Accuracy >= 90% en campos obligatorios
- STP (Straight-Through Processing) >= 60% (AUTO_APPROVE)
- Latencia P95 < 5 segundos (end-to-end)
- Disponibilidad >= 99.5%

## Fuera de alcance
- Integración SAP real (mock solamente)
- Multi-sede en operación (config preparada)
- Validaciones AFIP/ARCA
- Reentrenamiento de modelos
- Soporte para más de 3 proveedores
- Canales de ingesta alternativos (email, API)
