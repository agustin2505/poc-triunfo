# Triunfo — Spec-02 Agentes y Responsabilidades v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Agente A: Document AI (Extracción primaria)
- Motor principal de extracción
- Timeout: 15 segundos
- Salida: JSON con campos + confidence (0.0-1.0)
- Reintento: 1 vez en timeout
- Fallback: si falla → Agente C (Vertex)

## Agente B: Tesseract + Regex (OCR ligero)
- OCR local + regex para campos clave
- Timeout: 5 segundos
- Salida: campos extraídos vía regex (confidence basado en match exacto)
- Se ejecuta en paralelo con A para comparación
- No es bloqueante: si ambos fallan → Agente C
- Métrica: palabras claves encontradas, tiempo procesamiento

## Agente C: Vertex AI (Extracción fallback)
- Modelo generalista si A falla
- Timeout: 10 segundos
- Salida: campos + confidence normalizado
- Si también falla → rechazar documento (AUTO_REJECT)

## Agente D: Clasificador (Categoría + Proveedor)
- Keywords + modelo ligero para detectar tipo
- Timeout: 3 segundos
- Entrada: documento + raw_text
- Salida: category (SERVICIOS | FACTURA_NEGOCIO | OTRO), provider_id, confidence
- Si confidence < 0.70 → enrutar a HITL inmediatamente
- Métrica: tiempo de clasificación, accuracy contra ground truth

## Agente E: Validador/Normalizador (Post-procesamiento)
- Normaliza fechas (múltiples formatos), montos, moneda
- Aplica validaciones genéricas (positivos, lógica de fechas, duplicados)
- NO es bloqueante: avisos no reclasifican automáticamente
- Timeout: 2 segundos
- Salida: campos normalizados + lista de warnings
- Métrica: campos normalizados, validaciones ejecutadas

## Cadena de ejecución
1. Clasificador D (debe pasar para continuar)
2. Agentes A + B en paralelo (extracción)
3. Si ambos fallan: Agente C (fallback)
4. Agente E (validación + normalización)
5. Conciliación (mayoría entre A, B, C)
