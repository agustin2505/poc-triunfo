# Triunfo — Spec-04 Conciliación v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Entrada
Salidas de agentes A (DocumentAI), B (Tesseract), C (Vertex) con campos y confidences.

## Algoritmo de conciliación

### Para campos STRING (provider_name, reference_number)
- Mayoría simple: valor que aparezca en >= 2 agentes
- Empate: fallback a DocumentAI (A)
- Fuzzy match: si valores difieren pero son similares (Levenshtein >= 90%), usar valor de mayor confidence
- Si ambos agentes fallan (null): campo missing, no participa en scoring

### Para campos NUMERIC (total_amount)
- Si todos los valores están dentro del 5%: usar promedio ponderado por confidence
- Si hay desviación > 5%: usar mayoría simple (valor que aparezca >= 2 veces exacto)
- Si empate: usar valor de máxima confidence individual
- Penalización: confidence final = min(confidences) - 0.05 si hay desviación

### Para campos DATE (issue_date, due_date)
- Parsing flexible: aceptar DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY
- Mayoría simple: fecha normalizada que aparezca >= 2 veces
- Validación lógica: issue_date <= due_date (si ambas presentes)
- Si hay desviación: usar fecha con mayor confidence

### Confidence final por campo
```
confidence = average(confidences de agentes que concordaron)
- si hay conflicto (valores distintos): confidence *= 0.90
- si hay desviación numérica > 5%: confidence -= 0.05
- piso: 0.0, techo: 1.0
```

## Campos críticos
- provider_name, issue_date, total_amount
- Si confidence < 0.85 en alguno → HITL_STANDARD
- Si alguno falla completamente → HITL_PRIORITY (crítico)

## Scoring de confianza global
```
confidence_score = average(confidences de campos críticos)
- si alguna validación falla → penalización -0.10
- si hay warnings → penalización -0.05
```

## Enrutamiento basado en confidence_score
- >= 0.88 sin errores → AUTO_APPROVE
- 0.70-0.88 o warnings → HITL_STANDARD
- < 0.70 o validación falla → HITL_PRIORITY
- < 0.40 o clasificación falla → AUTO_REJECT
