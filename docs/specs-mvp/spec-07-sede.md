# Triunfo — Spec-07 Configuración por Sede v2.0
# Version: 2.0
# Fecha: 2026-04-14
# Estado: In Progress

```json
{
  "sede_id": "demo-001",
  "sede_name": "Sede Buenos Aires",
  "location": "CABA, Argentina",
  "currency": "ARS",
  "tax_context": "AR_CONSUMER",
  "tax_rates": {
    "iva": 21,
    "percepcion": 0,
    "otros": 0
  },
  "enabled_providers": [
    "edenor-001",
    "metrogas-001",
    "factura-interna-001"
  ],
  "sap_company_code": "AR00",
  "sap_chart_of_accounts": "AR",
  "hitl_sla_minutes": 120,
  "upload_channels": ["WEB"],
  "active": true,
  "created_at": "2026-04-01T00:00:00Z",
  "updated_at": "2026-04-14T00:00:00Z"
}
```

## Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| sede_id | string | ID único de sede |
| sede_name | string | Nombre descriptivo |
| location | string | Ubicación física |
| currency | string | Moneda (ARS, USD) |
| tax_context | string | Contexto fiscal (AR_CONSUMER, AR_BUSINESS, etc.) |
| tax_rates | object | Tasas impositivas aplicables |
| enabled_providers | array | IDs de proveedores activos en esta sede |
| sap_company_code | string | Código empresa en SAP |
| sap_chart_of_accounts | string | Plan de cuentas en SAP |
| hitl_sla_minutes | number | SLA para revisión HITL |
| upload_channels | array | Canales de ingesta permitidos (WEB, EMAIL, API) |
| active | bool | Si la sede está operativa |

## Contextos fiscales soportados (para futura expansión)
- AR_CONSUMER: Argentina, consumidor final
- AR_BUSINESS: Argentina, empresa
- BR_CONSUMER: Brasil, consumidor
- CL_BUSINESS: Chile, empresa
