export const TT = {
  primary: '#1B5E3F',
  primaryHover: '#134A30',
  primarySoft: '#E6F2EC',
  accent: '#5B2D7E',
  accentHover: '#4A2368',
  accentSoft: '#F0E9F5',
  background: '#F7F8FA',
  surface: '#FFFFFF',
  border: '#E5E7EB',
  divider: '#F1F2F4',
  fg: '#1F2937',
  muted: '#6B7280',
  subtle: '#9CA3AF',
  approve: { fg: '#15803D', bg: '#DCFCE7', solid: '#16A34A' },
  hitl: { fg: '#B45309', bg: '#FEF3C7', solid: '#D97706' },
  priority: { fg: '#C2410C', bg: '#FFEDD5', solid: '#EA580C' },
  reject: { fg: '#B91C1C', bg: '#FEE2E2', solid: '#DC2626' },
} as const

export type ToneKey = 'approve' | 'hitl' | 'priority' | 'reject'

export const ROUTING_META: Record<string, { tone: ToneKey; label: string; desc: string }> = {
  AUTO_APPROVE:  { tone: 'approve',  label: 'Auto-aprobado',       desc: 'Confidence alto en todos los campos críticos. Listo para SAP.' },
  HITL_STANDARD: { tone: 'hitl',     label: 'Revisión humana',      desc: 'Algunos campos por debajo de 0.88. Requiere revisión antes de SAP.' },
  HITL_PRIORITY: { tone: 'priority', label: 'Revisión prioritaria', desc: 'Confidence crítico en campos sensibles. Revisar primero.' },
  AUTO_REJECT:   { tone: 'reject',   label: 'Rechazado',            desc: 'Documento ilegible o no clasificable. No avanza al pipeline.' },
}

export function confBand(c: number): ToneKey {
  if (c >= 0.88) return 'approve'
  if (c >= 0.70) return 'hitl'
  if (c >= 0.40) return 'priority'
  return 'reject'
}

export function confColors(c: number) {
  return TT[confBand(c)]
}

export function confStatus(c: number): 'ok' | 'warn' | 'error' {
  if (c >= 0.88) return 'ok'
  if (c >= 0.40) return 'warn'
  return 'error'
}

export const FIELD_LABELS: Record<string, string> = {
  supplier_name: 'Nombre del proveedor',
  supplier_cuit: 'CUIT del proveedor',
  invoice_type: 'Tipo de factura',
  invoice_number: 'Número de factura',
  invoice_date: 'Fecha de factura',
  due_date: 'Fecha de vencimiento',
  currency: 'Moneda',
  net_amount: 'Importe neto',
  vat_amount: 'IVA',
  total_amount: 'Importe total',
  cae: 'CAE',
  cae_due_date: 'Vencimiento CAE',
  cuit_emisor: 'CUIT emisor',
  cuit_receptor: 'CUIT receptor',
  fecha: 'Fecha emisión',
  num_factura: 'Número factura',
  importe_total: 'Importe total',
  importe_iva: 'Importe IVA',
  periodo: 'Periodo facturado',
  cliente_codigo: 'Código cliente',
  medidor: 'Medidor / suministro',
  consumo_kwh: 'Consumo kWh',
}
