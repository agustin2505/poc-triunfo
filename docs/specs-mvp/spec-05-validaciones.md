# Triunfo — Spec-05 Validaciones v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Validaciones genéricas (para todos)

### Montos
- total_amount > 0
- total_amount <= 999999 (límite razonable)
- Sin caracteres especiales, solo números y punto decimal
- Si hay subtotal/neto/tax: subtotal + tax = total (tolerancia 0.01)

### Fechas
- issue_date válida (no futura, no anterior a 2020)
- Si due_date existe: issue_date <= due_date
- Si due_date existe: due_date <= issue_date + 180 días (máximo plazo razonable)

### Referencia
- reference_number no vacío (campo crítico)
- Formato alfanumérico, no caracteres especiales en exceso
- Longitud 5-30 caracteres

### Duplicados
- Check por (reference_number + provider + issue_date)
- Si existe registro anterior: marcar como DUPLICATE, rechazar
- Storage: en-memory para MVP, persistente en futura versión

## Validaciones específicas por proveedor

### Edenor (Servicios - Electricidad)
- meter_reading_end > meter_reading_start
- consumption > 0, <= 10000 kWh
- tariff_code no vacío
- tax rate = 21% (IVA fijo)
- period_end > period_start

### Metrogas (Servicios - Gas)
- consumption > 0, <= 5000 m³
- currency = ARS (moneda local)
- tax_rate en [0, 27] (rango válido IVA)
- period_end > period_start

### Factura Interna (Factura Negocio)
- sum(line_items.amount) = subtotal (tolerancia 0.01)
- subtotal + tax = total_amount
- tax_rate en [0, 27]
- item count >= 1
- cada item: quantity > 0, unit_price > 0

## Warnings (no bloquean, penalizan confidence)
- Monto fuera de rango normal para el proveedor (>2 desv. estándar)
- Período inusualmente largo (> 35 días para servicios)
- Confidence muy baja en campo no crítico (< 0.60)
- Falta campo recomendado (due_date, período)

## Errores críticos (bloquean, enrutan a HITL_PRIORITY)
- Validación aritmética falla
- Campo crítico falta completamente
- Duplicado detectado
- Formato inválido en campo estructurado
