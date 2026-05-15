"use client"

import { TT } from "@/lib/theme"
import type { PipelineStage } from "@/lib/mock-data"

interface ModelMetricsPanelProps {
  stages: PipelineStage[]
  confidenceScore: number
}

const STAGE_LABELS: Record<string, string> = {
  INGESTED:   "Ingresado",
  CLASSIFIED: "Clasificación",
  PROCESSING: "Procesando",
  EXTRACTED:  "Extracción",
  VALIDATED:  "Validación",
  ROUTED:     "Routing",
}

function KV({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: 13 }}>
      <span style={{ color: TT.muted }}>{label}</span>
      <span style={{ color: TT.fg, fontWeight: 500, fontFamily: mono ? 'monospace' : 'inherit', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </span>
    </div>
  )
}

export function ModelMetricsPanel({ stages, confidenceScore }: ModelMetricsPanelProps) {
  const total = stages.reduce((s, p) => s + p.duration_ms, 0)
  const stagesWithTime = stages.filter(s => s.duration_ms > 0)

  return (
    <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 16 }}>
        Modelos y métricas
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <KV label="Duración total" value={`${(total / 1000).toFixed(2)} s`} mono />
        <KV label="Confidence global" value={confidenceScore.toFixed(2)} mono />
        <KV label="Etapas completadas" value={`${stages.filter(s => s.status === 'SUCCESS').length} / ${stages.length}`} />
        <div style={{ height: 1, background: TT.divider, margin: '4px 0' }} />
        {stagesWithTime.map((s) => (
          <div key={s.name}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: TT.fg, fontWeight: 500 }}>{STAGE_LABELS[s.name] ?? s.name}</span>
              <span style={{ color: TT.muted, fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>
                {s.duration_ms} ms
              </span>
            </div>
            <div style={{ marginTop: 6, height: 3, background: TT.divider, borderRadius: 2, overflow: 'hidden' }}>
              <div style={{
                width: `${total > 0 ? Math.round((s.duration_ms / total) * 100) : 0}%`,
                height: '100%', background: TT.primary, transition: 'width 200ms ease',
              }} />
            </div>
          </div>
        ))}
        {stagesWithTime.length === 0 && (
          <div style={{ fontSize: 13, color: TT.muted, textAlign: 'center', padding: '8px 0' }}>
            Sin datos de duración
          </div>
        )}
      </div>
    </div>
  )
}
