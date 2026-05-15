"use client"

import { use, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, Loader2 } from "lucide-react"
import { TT } from "@/lib/theme"
import { ExtractedDataTable } from "@/components/extracted-data-table"
import { ModelMetricsPanel } from "@/components/model-metrics-panel"
import { ValidationPanel } from "@/components/validation-panel"
import { RoutingDecisionPanel } from "@/components/routing-decision-panel"
import { PipelineStepper } from "@/components/pipeline-stepper"
import type { ProcessedDocument } from "@/lib/mock-data"
import { getDocument, adaptDocument, approveDocument } from "@/lib/api"

interface PageProps {
  params: Promise<{ id: string }>
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20, ...style }}>
      {children}
    </div>
  )
}

function PanelLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 16 }}>
      {children}
    </div>
  )
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('es-AR', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

function formatSize(bytes: number) {
  if (!bytes) return '—'
  if (bytes > 1e6) return (bytes / 1e6).toFixed(1) + ' MB'
  return (bytes / 1024).toFixed(0) + ' KB'
}

export default function ResultadoPage({ params }: PageProps) {
  const { id } = use(params)
  const router = useRouter()
  const [document, setDocument] = useState<ProcessedDocument | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [approving, setApproving] = useState(false)
  const [approved, setApproved] = useState(false)
  const [toast, setToast] = useState('')

  useEffect(() => {
    getDocument(id)
      .then(raw => { setDocument(adaptDocument(raw)); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [id])

  const handleApprove = async () => {
    if (!document) return
    setApproving(true)
    try {
      await approveDocument(document.document_id)
      setApproved(true)
      setToast(`Documento enviado a SAP · ${document.document_id}`)
      setTimeout(() => setToast(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al enviar a SAP')
    } finally {
      setApproving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 12, color: TT.muted }}>
        <Loader2 size={20} className="animate-spin" /> Cargando resultado…
      </div>
    )
  }

  if (error && !document) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 16 }}>
        <div style={{ fontSize: 15, color: TT.reject.fg, fontWeight: 500 }}>{error}</div>
        <button onClick={() => router.push('/')} style={{
          height: 38, padding: '0 16px', fontSize: 14, fontWeight: 500, borderRadius: 8,
          background: TT.surface, color: TT.fg, border: `1px solid ${TT.border}`, cursor: 'pointer',
        }}>
          Volver al inicio
        </button>
      </div>
    )
  }

  const doc = document!
  const totalMs = doc.stages.reduce((s, p) => s + p.duration_ms, 0)
  const displayName = doc.filename.replace(/\.(pdf|png|jpg|jpeg)$/i, '').toUpperCase()

  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '24px 32px 64px' }}>
      {/* Back button */}
      <button
        onClick={() => router.push('/cola-hitl')}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer', color: TT.muted,
          fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: 0, fontFamily: 'inherit', marginBottom: 16, transition: 'color 150ms ease',
        }}
        onMouseEnter={e => (e.currentTarget.style.color = TT.primary)}
        onMouseLeave={e => (e.currentTarget.style.color = TT.muted)}
      >
        <ArrowLeft size={14} /> Volver a la cola
      </button>

      {/* Title row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Factura · {doc.provider}
          </div>
          <h1 style={{
            fontSize: 28, fontWeight: 700, letterSpacing: '-.01em', margin: '6px 0 0', lineHeight: 1.28,
            color: TT.fg, fontFamily: 'monospace',
          }}>
            {displayName}
          </h1>
          <div style={{ display: 'flex', gap: 16, fontSize: 13, color: TT.muted, marginTop: 8, flexWrap: 'wrap' }}>
            <span><span style={{ color: TT.subtle }}>doc_id</span> <span style={{ fontFamily: 'monospace' }}>{doc.document_id}</span></span>
            {doc.filesize > 0 && <><span>·</span><span>{formatSize(doc.filesize)}</span></>}
            <span>·</span>
            <span>procesado {formatDate(doc.created_at)}</span>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ background: '#FEF2F2', border: `1px solid #FECACA`, borderRadius: 8, padding: '12px 16px', fontSize: 14, color: '#B91C1C', marginBottom: 20 }}>
          {error}
        </div>
      )}

      {/* Hero · Routing decision */}
      <div style={{ marginBottom: 20 }}>
        <RoutingDecisionPanel
          doc={doc}
          onApprove={handleApprove}
          onBack={() => router.push('/cola-hitl')}
          approving={approving}
          approved={approved}
        />
      </div>

      {/* Pipeline stepper */}
      {doc.stages.length > 0 && (
        <Card style={{ marginBottom: 20 }}>
          <PanelLabel>Pipeline · {(totalMs / 1000).toFixed(2)} s · {doc.stages.length} etapas</PanelLabel>
          <PipelineStepper stages={doc.stages} />
        </Card>
      )}

      {/* Grid: data left + sidebar right */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 20, alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 12 }}>
            Datos extraídos · {Object.keys(doc.extracted_fields).length} campos
          </div>
          <ExtractedDataTable fields={doc.extracted_fields} routing={doc.routing} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <ValidationPanel validation={doc.validation} />
          <ModelMetricsPanel stages={doc.stages} confidenceScore={doc.confidence_score} />
        </div>
      </div>

      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: TT.fg, color: '#fff',
          padding: '12px 16px', borderRadius: 10, fontSize: 14, fontWeight: 500,
          boxShadow: '0 12px 32px -8px rgba(16,24,40,.4)', zIndex: 100,
          display: 'flex', alignItems: 'center', gap: 10,
        }} role="status">
          <span style={{ color: TT.approve.solid, display: 'inline-flex' }}>✓</span> {toast}
        </div>
      )}
    </div>
  )
}
