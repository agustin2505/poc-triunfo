// Cliente API para el backend Triunfo (FastAPI en localhost:8000)

import type {
  ProcessedDocument,
  ExtractedField,
  PipelineStage,
  RoutingDecision,
  FieldSource,
  StageStatus,
} from "./mock-data"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ---------------------------------------------------------------------------
// Tipos del backend
// ---------------------------------------------------------------------------

export interface BackendFieldValue {
  value: string | number | null
  confidence: number
}

export interface BackendConciliationField {
  value: string | number | null
  confidence: number
  source: string
  sources_detail: Record<string, BackendFieldValue>
}

export interface BackendStageInfo {
  name: string
  duration_ms: number
  status: string
}

export interface BackendProcessingSummary {
  total_duration_ms: number
  stages: BackendStageInfo[]
  models_used: string[]
  missing_fields: string[]
}

export interface BackendValidation {
  is_consistent: boolean
  errors: string[]
  warnings: string[]
}

export interface BackendIngestion {
  document_id: string
  file_name: string
  file_size_bytes: number
  uploaded_at: string
  sede_id: string
}

export interface BackendDocumentResult {
  document_id: string
  status: string
  category: string | null
  provider: string | null
  provider_id: string | null
  confidence_score: number
  extracted_fields: Record<string, BackendConciliationField>
  validation: BackendValidation | null
  routing: string | null
  routing_reason: string | null
  processing_summary: BackendProcessingSummary | null
  ingestion: BackendIngestion | null
  sap_response: Record<string, unknown> | null
}

export interface BackendDocumentListItem {
  document_id: string
  status: string
  provider: string | null
  routing: string | null
  confidence_score: number
  file_name: string
  uploaded_at: string
}

export interface BackendDocumentList {
  total: number
  returned: number
  documents: BackendDocumentListItem[]
}

// ---------------------------------------------------------------------------
// Adaptadores: backend → frontend
// ---------------------------------------------------------------------------

function mapSource(source: string): FieldSource {
  switch (source) {
    case "majority": return "majority"
    case "agent_a": return "docai"
    case "agent_b": return "tesseract"
    case "agent_c": return "vertex"
    default: return "missing"
  }
}

function mapStageStatus(status: string): StageStatus {
  switch (status) {
    case "SUCCESS": return "SUCCESS"
    case "FAILED": return "FAILED"
    case "SKIPPED": return "SKIPPED"
    case "TIMEOUT": return "FAILED"
    default: return "PENDING"
  }
}

export function adaptDocument(raw: BackendDocumentResult): ProcessedDocument {
  const extracted_fields: Record<string, ExtractedField> = {}
  for (const [key, field] of Object.entries(raw.extracted_fields || {})) {
    extracted_fields[key] = {
      value: field.value,
      confidence: field.confidence,
      source: mapSource(field.source),
      agentA: field.sources_detail?.agent_a
        ? { value: field.sources_detail.agent_a.value, confidence: field.sources_detail.agent_a.confidence }
        : undefined,
      agentB: field.sources_detail?.agent_b
        ? { value: field.sources_detail.agent_b.value, confidence: field.sources_detail.agent_b.confidence }
        : undefined,
      agentC: field.sources_detail?.agent_c
        ? { value: field.sources_detail.agent_c.value, confidence: field.sources_detail.agent_c.confidence }
        : undefined,
    }
  }

  const stages: PipelineStage[] = raw.processing_summary?.stages?.map((s) => ({
    name: s.name,
    duration_ms: s.duration_ms,
    status: mapStageStatus(s.status),
  })) ?? [
    { name: "INGESTED", duration_ms: 0, status: "SUCCESS" },
    { name: "CLASSIFIED", duration_ms: 0, status: "SUCCESS" },
    { name: "PROCESSING", duration_ms: 0, status: "SUCCESS" },
    { name: "EXTRACTED", duration_ms: 0, status: "SUCCESS" },
    { name: "VALIDATED", duration_ms: 0, status: "SUCCESS" },
    { name: "ROUTED", duration_ms: 0, status: "SUCCESS" },
  ]

  return {
    document_id: raw.document_id,
    provider: raw.provider || "Desconocido",
    category: raw.category || "OTRO",
    routing: (raw.routing || "AUTO_REJECT") as RoutingDecision,
    routing_reason: raw.routing_reason ?? undefined,
    confidence_score: raw.confidence_score,
    extracted_fields,
    stages,
    validation: raw.validation ?? { is_consistent: true, errors: [], warnings: [] },
    created_at: raw.ingestion?.uploaded_at || new Date().toISOString(),
    filename: raw.ingestion?.file_name || "documento",
    filesize: raw.ingestion?.file_size_bytes || 0,
  }
}

export function adaptListItem(item: BackendDocumentListItem): ProcessedDocument {
  return {
    document_id: item.document_id,
    provider: item.provider || "Desconocido",
    category: "—",
    routing: (item.routing || "AUTO_REJECT") as RoutingDecision,
    confidence_score: item.confidence_score,
    extracted_fields: {},
    stages: [],
    validation: { is_consistent: true, errors: [], warnings: [] },
    created_at: item.uploaded_at,
    filename: item.file_name,
    filesize: 0,
  }
}

// ---------------------------------------------------------------------------
// Mapeo de valores del formulario
// ---------------------------------------------------------------------------

const QUALITY_MAP: Record<string, string> = {
  buena: "good",
  media: "medium",
  mala: "poor",
}

const PROVIDER_MAP: Record<string, string> = {
  edenor: "edenor-001",
  metrogas: "metrogas-001",
  interna: "factura-interna-001",
}

// ---------------------------------------------------------------------------
// Funciones API
// ---------------------------------------------------------------------------

export async function uploadDocument(
  file: File,
  options: { providerHint?: string; qualityHint?: string } = {}
): Promise<BackendDocumentResult> {
  const formData = new FormData()
  formData.append("file", file)

  const mappedProvider = options.providerHint ? PROVIDER_MAP[options.providerHint] : undefined
  if (mappedProvider) formData.append("provider_hint", mappedProvider)

  formData.append("quality_hint", QUALITY_MAP[options.qualityHint || "buena"] || "good")

  const res = await fetch(`${API_URL}/upload`, { method: "POST", body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error desconocido" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getDocument(id: string): Promise<BackendDocumentResult> {
  const res = await fetch(`${API_URL}/document/${id}`)
  if (!res.ok) throw new Error(`Documento no encontrado: ${id}`)
  return res.json()
}

export async function listDocuments(limit = 100): Promise<BackendDocumentList> {
  const res = await fetch(`${API_URL}/documents?limit=${limit}`)
  if (!res.ok) throw new Error("Error al obtener documentos")
  return res.json()
}

// ---------------------------------------------------------------------------
// Métricas
// ---------------------------------------------------------------------------

export interface BackendAgentStat {
  name: string
  invocations: number
  successes: number
  success_rate: number
  timeout_rate: number
  avg_duration_ms: number
  avg_confidence: number
}

export interface BackendMetrics {
  total_documents: number
  routing_distribution: Record<string, number>
  latency_p95_ms: number
  agent_stats: BackendAgentStat[]
  confidence_distribution: Record<string, Record<string, number>>
}

export async function getMetrics(): Promise<BackendMetrics> {
  const res = await fetch(`${API_URL}/metrics`)
  if (!res.ok) throw new Error("Error al obtener métricas")
  return res.json()
}

export async function approveDocument(id: string): Promise<unknown> {
  const res = await fetch(`${API_URL}/document/${id}/approve`, { method: "POST" })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error al enviar a SAP" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}
