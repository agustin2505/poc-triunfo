# Triunfo — Spec-08 SAP Mock v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Request
```json
{
  "request_id": "uuid-v4",
  "document_id": "uuid-v4",
  "sede_id": "demo-001",
  "provider": "Edenor",
  "provider_id": "edenor-001",
  "reference_number": "0001-00012345",
  "total_amount": 12345.67,
  "currency": "ARS",
  "issue_date": "2026-03-01",
  "sap_company_code": "AR00",
  "sap_account_code": "6000",
  "extracted_fields": {
    "provider_name": "Edenor",
    "meter_reading": "123456"
  }
}
```

## Response - OK
```json
{
  "request_id": "uuid-v4",
  "status": "SUCCESS",
  "sap_document_number": "4900001234",
  "sap_posting_date": "2026-04-14",
  "message": "Documento creado exitosamente en SAP",
  "audit": {
    "created_by": "TRIUNFO_SYSTEM",
    "created_at": "2026-04-14T12:30:45Z"
  }
}
```

## Response - Duplicate
```json
{
  "request_id": "uuid-v4",
  "status": "DUPLICATE",
  "sap_document_number": "4900001200",
  "message": "Documento duplicado detectado",
  "existing_document": {
    "reference_number": "0001-00012345",
    "provider": "Edenor",
    "amount": 12345.67,
    "posted_date": "2026-04-13"
  }
}
```

## Response - Validation Error
```json
{
  "request_id": "uuid-v4",
  "status": "VALIDATION_ERROR",
  "message": "Validación SAP fallida",
  "errors": [
    "Monto excede límite permitido",
    "Código de cuenta inválido"
  ]
}
```

## Response - Internal Error
```json
{
  "request_id": "uuid-v4",
  "status": "INTERNAL_ERROR",
  "message": "Error al procesar en SAP",
  "error_code": "TIMEOUT|SERVICE_UNAVAILABLE|UNKNOWN"
}
```

## Lógica mock
- Generar SAP_DOCUMENT_NUMBER: 4900000000 + random(1-999999)
- Check duplicados: (reference_number, provider, amount) en memoria
- Si suma de requests en último minuto > 100: retornar INTERNAL_ERROR (simular límite)
- Posting date: siempre hoy
- Success rate: 95% (5% error aleatorio para testing)
