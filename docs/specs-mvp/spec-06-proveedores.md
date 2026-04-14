# Triunfo — Spec-06 Catálogo de Proveedores v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

## Proveedores demo (3 iniciales)

### Edenor
```json
{
  "provider_id": "edenor-001",
  "provider_name": "Edenor",
  "category": "SERVICIOS",
  "keywords": ["edenor", "electricidad", "kwh", "factura luz", "medidor", "distribuidora"],
  "active": true,
  "schema": {
    "required": ["provider_name", "issue_date", "total_amount"],
    "optional": ["due_date", "reference_number", "meter_reading_start", "meter_reading_end", "consumption", "tariff_code"]
  },
  "validation_rules": {
    "consumption_range": [0, 10000],
    "tax_rate": 21,
    "currency": "ARS"
  },
  "sap_mapping": {
    "provider_name": "VENDOR_CODE",
    "reference_number": "INVOICE_NO",
    "total_amount": "GROSS_AMOUNT",
    "issue_date": "DOCUMENT_DATE",
    "currency": "CURRENCY_KEY"
  }
}
```

### Metrogas
```json
{
  "provider_id": "metrogas-001",
  "provider_name": "Metrogas",
  "category": "SERVICIOS",
  "keywords": ["metrogas", "gas", "m3", "factura gas", "gasoducto"],
  "active": true,
  "schema": {
    "required": ["provider_name", "issue_date", "total_amount"],
    "optional": ["due_date", "reference_number", "consumption", "meter_reading_start", "meter_reading_end"]
  },
  "validation_rules": {
    "consumption_range": [0, 5000],
    "tax_rate": [0, 27],
    "currency": "ARS"
  },
  "sap_mapping": {
    "provider_name": "VENDOR_CODE",
    "reference_number": "INVOICE_NO",
    "total_amount": "GROSS_AMOUNT",
    "issue_date": "DOCUMENT_DATE",
    "currency": "CURRENCY_KEY"
  }
}
```

### Factura Interna
```json
{
  "provider_id": "factura-interna-001",
  "provider_name": "Nuestra Empresa",
  "category": "FACTURA_NEGOCIO",
  "keywords": ["factura", "comprobante", "empresa", "venta", "servicio"],
  "active": true,
  "schema": {
    "required": ["provider_name", "issue_date", "total_amount"],
    "optional": ["due_date", "reference_number", "subtotal", "tax_amount", "tax_rate", "line_items"]
  },
  "validation_rules": {
    "tax_rate": [0, 27],
    "currency": "ARS",
    "item_count_min": 1
  },
  "sap_mapping": {
    "provider_name": "CUSTOMER_CODE",
    "reference_number": "SALES_ORDER",
    "total_amount": "GROSS_AMOUNT",
    "issue_date": "DOCUMENT_DATE",
    "currency": "CURRENCY_KEY"
  }
}
```

## Estructura general proveedor
```json
{
  "provider_id": "unique-id",
  "provider_name": "Display name",
  "category": "SERVICIOS | FACTURA_NEGOCIO | OTRO",
  "keywords": ["list", "of", "keywords"],
  "active": true,
  "schema": {
    "required": ["field1", "field2"],
    "optional": ["field3", "field4"]
  },
  "validation_rules": {
    "campo": {"type": "numeric|string|date", "min": 0, "max": 999999, "pattern": null}
  },
  "sap_mapping": {
    "document_field": "SAP_FIELD"
  }
}
```
