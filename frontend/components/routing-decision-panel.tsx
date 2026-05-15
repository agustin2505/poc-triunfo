"use client"

import { Send, Download, ArrowLeft, Loader2 } from "lucide-react"
import { TT, ROUTING_META } from "@/lib/theme"
import { RoutingBadge } from "@/components/routing-badge"
import type { RoutingDecision, ProcessedDocument } from "@/lib/mock-data"

interface RoutingDecisionPanelProps {
  doc: ProcessedDocument
  onApprove?: () => void
  onBack?: () => void
  approving?: boolean
  approved?: boolean
}

export function RoutingDecisionPanel({ doc, onApprove, onBack, approving, approved }: RoutingDecisionPanelProps) {
  const meta = ROUTING_META[doc.routing] ?? ROUTING_META.AUTO_REJECT
  const colors = TT[meta.tone]

  const fieldCount = Object.keys(doc.extracted_fields).length
  const lowConfCount = Object.values(doc.extracted_fields).filter(f => f.confidence < 0.88).length
  const errorCount = doc.validation.errors.length
  const totalMs = doc.stages.reduce((s, p) => s + p.duration_ms, 0)

  const handleJsonDownload = () => {
    const payload = {
      document_id: doc.document_id,
      provider: doc.provider,
      routing: doc.routing,
      score: doc.confidence_score,
      fields: Object.fromEntries(
        Object.entries(doc.extracted_fields).map(([k, v]) => [k, { value: v.value, confidence: v.confidence, source: v.source }])
      ),
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = Object.assign(document.createElement('a'), { href: url, download: `${doc.document_id}.json` })
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{
      background: TT.surface, border: `1px solid ${TT.border}`,
      borderLeft: `4px solid ${colors.solid}`, borderRadius: 12, padding: 24,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 360px', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <RoutingBadge routing={doc.routing as RoutingDecision} size="lg" />
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontSize: 12, color: TT.muted, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '.06em' }}>
                Score
              </span>
              <span style={{ fontSize: 22, fontWeight: 700, fontFamily: 'monospace', color: colors.fg, fontVariantNumeric: 'tabular-nums' }}>
                {doc.confidence_score.toFixed(2)}
              </span>
            </div>
          </div>
          <div style={{ fontSize: 15, color: TT.fg, lineHeight: 1.55 }}>{meta.desc}</div>
          <div style={{ marginTop: 12, display: 'flex', gap: 16, fontSize: 12, color: TT.muted }}>
            <span><strong style={{ color: TT.fg, fontWeight: 600 }}>{lowConfCount}</strong> campos &lt; 0.88</span>
            <span><strong style={{ color: TT.fg, fontWeight: 600 }}>{errorCount}</strong> con error</span>
            {totalMs > 0 && <span><strong style={{ color: TT.fg, fontWeight: 600 }}>{(totalMs / 1000).toFixed(2)} s</strong> pipeline</span>}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'stretch', minWidth: 200 }}>
          <button
            onClick={onApprove}
            disabled={approving || approved}
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              height: 38, padding: '0 14px', fontSize: 14, fontWeight: 500, borderRadius: 8,
              background: approved ? TT.approve.bg : TT.approve.solid, color: approved ? TT.approve.fg : '#fff',
              border: 'none', cursor: approving || approved ? 'not-allowed' : 'pointer',
              opacity: approving ? 0.7 : 1, transition: 'all 150ms ease',
            }}
          >
            {approving ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            {approved ? 'Enviado a SAP' : 'Aprobar y enviar a SAP'}
          </button>

          <button
            onClick={handleJsonDownload}
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              height: 38, padding: '0 14px', fontSize: 14, fontWeight: 500, borderRadius: 8,
              background: TT.surface, color: TT.primary, border: `1px solid ${TT.primary}`,
              cursor: 'pointer', transition: 'all 150ms ease',
            }}
          >
            <Download size={15} /> Exportar JSON
          </button>

          {onBack && (
            <button
              onClick={onBack}
              style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                height: 38, padding: '0 14px', fontSize: 14, fontWeight: 500, borderRadius: 8,
                background: 'transparent', color: TT.fg, border: 'none',
                cursor: 'pointer', transition: 'all 150ms ease',
              }}
            >
              <ArrowLeft size={15} /> Volver a la cola
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
