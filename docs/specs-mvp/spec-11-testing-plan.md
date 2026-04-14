# Triunfo — Spec-11 Testing Plan v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Estrategia de testing

### 1. Unit Tests
Validaciones genéricas, parsers de fechas, normalizadores:
- Test unitarios por función (validación, normalización)
- Coverage: >= 80% en lógica crítica
- Runner: pytest

### 2. Integration Tests
Pipeline completo (ingesta -> conciliación -> validación):
- Mock de agentes extrae datos consistentes
- Validaciones ejecutan correctamente
- Conciliación produce resultado esperado

### 3. End-to-End Tests (Golden Set)
Usando manifesto de datos de prueba:
- Procesar 30 documentos del golden set
- Comparar extracted_fields vs expected_fields
- Métricas:
  - Accuracy por proveedor: >= 90%
  - STP (AUTO_APPROVE rate): >= 60%
  - Falsos positivos (AUTO_APPROVE de low-quality): 0%

### 4. Performance Tests
- Latencia P95 < 5 segundos (clasificación + extracción + validación)
- Concurrency: 10 documentos simultáneos sin degradación

### 5. Edge Cases (Manual + Automated)

#### Documentos problemáticos
- Imagen rotada 45 grados
- Imagen muy borrosa (simulada)
- Imagen con texto sobrepuesto
- Página en blanco
- Documento cortado (falta mitad inferior)

#### Validaciones edge case
- Monto = 0.01 (mínimo)
- Monto = 999999 (máximo)
- Fecha futura (hoy + 1 día)
- Duplicado exacto (ref + provider + date)
- Campo crítico null/missing
- Desviación numérica 4.99% entre agentes

#### Conciliación edge case
- 2 agentes coinciden, 1 discrepa
- Todos 3 discrepan (fallback a A)
- Fuzzy match: "Edenor" vs "EDENOR" vs "Ednor"
- Valores numéricos: 12345.67 vs 12345.68 vs 12345.70

## Checklist de prueba antes de release

Funcionalidad:
- [ ] Upload de documento
- [ ] Clasificación detecta proveedor correcto
- [ ] Extracción trae valores correctos
- [ ] Conciliación produce resultado consistente
- [ ] Validaciones pasan/fallan según regla
- [ ] Enrutamiento es correcto (AUTO_APPROVE vs HITL)
- [ ] SAP mock recibe y responde

UI:
- [ ] Tabla de datos extraídos se llena correctamente
- [ ] Métricas de modelos muestran duración por etapa
- [ ] Confidence scores son visibles
- [ ] Warnings se muestran en rojo/naranja
- [ ] Botón Approve está habilitado solo si AUTO_APPROVE
- [ ] Responsive en mobile/tablet/desktop

Performance:
- [ ] Documento buenos: < 3s total
- [ ] Documento mediocre: < 5s total
- [ ] 10 documentos simultáneos: sin errores
- [ ] Memory leak check (proceso posterior de 100 docs)

## Métricas baseline (target MVP)
```
Accuracy:
- Edenor: >= 92%
- Metrogas: >= 90%
- Factura Interna: >= 88%

STP:
- Edenor good: >= 75%
- Metrogas good: >= 70%
- Factura Interna good: >= 65%

Routing correctness:
- No falsos positivos (low-quality en AUTO_APPROVE): 0%
- Cobertura (documentos procesados): 100%

Latencia P95: < 5s
Latencia P99: < 8s
```

## Script de testing
```bash
# Run all tests
pytest ./tests/ -v --cov=./src

# Run golden set validation
python ./scripts/validate-golden-set.py --manifest ./docs/specs-mvp/golden-set-manifest.json

# Run performance test
python ./scripts/perf-test.py --documents 30 --concurrent 10

# Generate report
python ./scripts/test-report.py --output ./test-results.html
```