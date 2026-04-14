// Mock data for Triunfo OCR/IDP Pipeline Dashboard

export type RoutingDecision = "AUTO_APPROVE" | "HITL_STANDARD" | "HITL_PRIORITY" | "AUTO_REJECT"
export type StageStatus = "SUCCESS" | "FAILED" | "SKIPPED" | "PENDING" | "PROCESSING"
export type FieldSource = "majority" | "docai" | "tesseract" | "vertex" | "missing"

export interface ExtractedField {
  value: string | number | null
  confidence: number
  source: FieldSource
  agentA?: { value: string | number | null; confidence: number } // DocAI
  agentB?: { value: string | number | null; confidence: number } // Tesseract
  agentC?: { value: string | number | null; confidence: number } // Vertex
}

export interface PipelineStage {
  name: string
  duration_ms: number
  status: StageStatus
}

export interface DocumentValidation {
  is_consistent: boolean
  errors: string[]
  warnings: string[]
}

export interface ProcessedDocument {
  document_id: string
  provider: string
  category: string
  routing: RoutingDecision
  confidence_score: number
  extracted_fields: Record<string, ExtractedField>
  stages: PipelineStage[]
  validation: DocumentValidation
  created_at: string
  filename: string
  filesize: number
}

export const mockDocument: ProcessedDocument = {
  document_id: "a1b2c3d4",
  provider: "Edenor",
  category: "SERVICIOS",
  routing: "AUTO_APPROVE",
  confidence_score: 0.92,
  filename: "factura_edenor_marzo_2026.pdf",
  filesize: 245760,
  created_at: "2026-03-15T10:30:00Z",
  extracted_fields: {
    supplier_name: { 
      value: "Edenor S.A.", 
      confidence: 0.96, 
      source: "majority",
      agentA: { value: "Edenor S.A.", confidence: 0.96 },
      agentB: { value: "Edenor S.A.", confidence: 0.94 },
      agentC: { value: null, confidence: 0 }
    },
    supplier_cuit: { 
      value: "30-64407869-6", 
      confidence: 0.94, 
      source: "majority",
      agentA: { value: "30-64407869-6", confidence: 0.95 },
      agentB: { value: "30-64407869-6", confidence: 0.93 },
      agentC: { value: null, confidence: 0 }
    },
    invoice_type: { 
      value: "B", 
      confidence: 0.99, 
      source: "docai",
      agentA: { value: "B", confidence: 0.99 },
      agentB: { value: "B", confidence: 0.85 },
      agentC: { value: null, confidence: 0 }
    },
    invoice_number: { 
      value: "0002-00034521", 
      confidence: 0.91, 
      source: "majority",
      agentA: { value: "0002-00034521", confidence: 0.92 },
      agentB: { value: "0002-00034521", confidence: 0.90 },
      agentC: { value: null, confidence: 0 }
    },
    invoice_date: { 
      value: "2026-03-01", 
      confidence: 0.90, 
      source: "majority",
      agentA: { value: "2026-03-01", confidence: 0.91 },
      agentB: { value: "2026-03-01", confidence: 0.89 },
      agentC: { value: null, confidence: 0 }
    },
    due_date: { 
      value: null, 
      confidence: 0.0, 
      source: "missing",
      agentA: { value: null, confidence: 0 },
      agentB: { value: null, confidence: 0 },
      agentC: { value: null, confidence: 0 }
    },
    currency: { 
      value: "ARS", 
      confidence: 0.99, 
      source: "docai",
      agentA: { value: "ARS", confidence: 0.99 },
      agentB: { value: "ARS", confidence: 0.95 },
      agentC: { value: null, confidence: 0 }
    },
    net_amount: { 
      value: 10202.21, 
      confidence: 0.93, 
      source: "majority",
      agentA: { value: 10202.21, confidence: 0.94 },
      agentB: { value: 10202.21, confidence: 0.92 },
      agentC: { value: null, confidence: 0 }
    },
    vat_amount: { 
      value: 2142.46, 
      confidence: 0.89, 
      source: "majority",
      agentA: { value: 2142.46, confidence: 0.90 },
      agentB: { value: 2142.46, confidence: 0.88 },
      agentC: { value: null, confidence: 0 }
    },
    total_amount: { 
      value: 12344.67, 
      confidence: 0.94, 
      source: "majority",
      agentA: { value: 12344.67, confidence: 0.95 },
      agentB: { value: 12344.67, confidence: 0.93 },
      agentC: { value: null, confidence: 0 }
    },
    cae: { 
      value: "72415663825491", 
      confidence: 0.88, 
      source: "majority",
      agentA: { value: "72415663825491", confidence: 0.89 },
      agentB: { value: "72415663825491", confidence: 0.87 },
      agentC: { value: null, confidence: 0 }
    },
    cae_due_date: { 
      value: "2026-03-11", 
      confidence: 0.87, 
      source: "tesseract",
      agentA: { value: "2026-03-10", confidence: 0.82 },
      agentB: { value: "2026-03-11", confidence: 0.87 },
      agentC: { value: null, confidence: 0 }
    }
  },
  stages: [
    { name: "INGESTED", duration_ms: 120, status: "SUCCESS" },
    { name: "CLASSIFIED", duration_ms: 800, status: "SUCCESS" },
    { name: "PROCESSING", duration_ms: 100, status: "SUCCESS" },
    { name: "EXTRACTED", duration_ms: 1600, status: "SUCCESS" },
    { name: "VALIDATED", duration_ms: 250, status: "SUCCESS" },
    { name: "ROUTED", duration_ms: 150, status: "SUCCESS" }
  ],
  validation: {
    is_consistent: true,
    errors: [],
    warnings: ["Low confidence en cae_due_date (0.87)", "Campo due_date no extraído"]
  }
}

export const mockHITLDocument: ProcessedDocument = {
  ...mockDocument,
  document_id: "e5f6g7h8",
  routing: "HITL_STANDARD",
  confidence_score: 0.78,
  provider: "Metrogas",
  category: "SERVICIOS",
  filename: "factura_metrogas_feb_2026.pdf",
  validation: {
    is_consistent: false,
    errors: ["Discrepancia en total_amount entre agentes"],
    warnings: ["Low confidence en supplier_cuit (0.72)", "Low confidence en invoice_number (0.75)"]
  }
}

export const mockDocuments: ProcessedDocument[] = [
  mockDocument,
  mockHITLDocument,
  {
    ...mockDocument,
    document_id: "i9j0k1l2",
    routing: "HITL_PRIORITY",
    confidence_score: 0.65,
    provider: "Factura Interna",
    category: "INTERNO",
    filename: "factura_interna_001.pdf"
  },
  {
    ...mockDocument,
    document_id: "m3n4o5p6",
    routing: "AUTO_REJECT",
    confidence_score: 0.42,
    provider: "Desconocido",
    category: "NO_CLASIFICADO",
    filename: "documento_ilegible.jpg",
    validation: {
      is_consistent: false,
      errors: ["Documento ilegible", "No se pudo identificar el proveedor", "Campos críticos faltantes"],
      warnings: []
    }
  }
]

// Metrics mock data
export const mockMetrics = {
  docsProcessedToday: 147,
  stpRate: 0.73,
  latencyP95: 4.2,
  errorRate: 0.02,
  routingDistribution: {
    AUTO_APPROVE: 108,
    HITL_STANDARD: 24,
    HITL_PRIORITY: 12,
    AUTO_REJECT: 3
  },
  agentStats: [
    { name: "DocAI", invocations: 147, successes: 144, successRate: 0.98, timeoutRate: 0.01, avgDuration: 1.2, avgConfidence: 0.91 },
    { name: "Tesseract", invocations: 147, successes: 145, successRate: 0.99, timeoutRate: 0.005, avgDuration: 0.4, avgConfidence: 0.85 },
    { name: "Vertex", invocations: 39, successes: 36, successRate: 0.92, timeoutRate: 0.03, avgDuration: 2.1, avgConfidence: 0.88 }
  ],
  confidenceDistribution: {
    "0-0.5": { docai: 2, tesseract: 5, vertex: 3 },
    "0.5-0.7": { docai: 8, tesseract: 15, vertex: 8 },
    "0.7-0.85": { docai: 35, tesseract: 52, vertex: 12 },
    "0.85-1.0": { docai: 102, tesseract: 75, vertex: 16 }
  }
}

// Field labels in Spanish
export const fieldLabels: Record<string, string> = {
  supplier_name: "Nombre del proveedor",
  supplier_cuit: "CUIT del proveedor",
  invoice_type: "Tipo de factura",
  invoice_number: "Número de factura",
  invoice_date: "Fecha de factura",
  due_date: "Fecha de vencimiento",
  currency: "Moneda",
  net_amount: "Importe neto",
  vat_amount: "IVA",
  total_amount: "Importe total",
  cae: "CAE",
  cae_due_date: "Vencimiento CAE"
}

// Critical fields that should be highlighted
export const criticalFields = ["supplier_name", "invoice_date", "total_amount"]

// Helper functions
export function formatCurrency(amount: number | null): string {
  if (amount === null) return "—"
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2
  }).format(amount)
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—"
  const date = new Date(dateStr)
  return date.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  })
}

export function formatConfidence(confidence: number): string {
  return confidence.toFixed(2)
}

export function getConfidenceColor(confidence: number): "green" | "yellow" | "red" {
  if (confidence >= 0.88) return "green"
  if (confidence >= 0.70) return "yellow"
  return "red"
}

export function getRoutingColor(routing: RoutingDecision): string {
  switch (routing) {
    case "AUTO_APPROVE": return "green"
    case "HITL_STANDARD": return "yellow"
    case "HITL_PRIORITY": return "orange"
    case "AUTO_REJECT": return "red"
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
