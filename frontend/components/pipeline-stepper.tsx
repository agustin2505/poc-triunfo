"use client"

import { Check, AlertTriangle, Loader2 } from "lucide-react"
import { TT } from "@/lib/theme"
import type { PipelineStage, StageStatus } from "@/lib/mock-data"

const STAGE_LABELS: Record<string, string> = {
  INGESTED:   "Ingresado",
  CLASSIFIED: "Clasificación",
  PROCESSING: "Procesando",
  EXTRACTED:  "Extracción",
  VALIDATED:  "Validación",
  ROUTED:     "Routing",
}

interface PipelineStepperProps {
  stages: PipelineStage[]
  currentIdx?: number
  animated?: boolean
}

function DotContent({ status, animated, isCurrent, index }: {
  status: StageStatus
  animated?: boolean
  isCurrent?: boolean
  index: number
}) {
  if (animated && isCurrent) {
    return (
      <span style={{
        width: 8, height: 8, borderRadius: 999, background: TT.primary,
        animation: 'pulse 1s ease infinite',
      }} />
    )
  }
  if (status === 'SUCCESS') return <Check size={13} />
  if (status === 'FAILED') return <AlertTriangle size={13} />
  if (status === 'PROCESSING') return <Loader2 size={13} className="animate-spin" />
  return <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'monospace' }}>{index + 1}</span>
}

export function PipelineStepper({ stages, currentIdx, animated }: PipelineStepperProps) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, overflowX: 'auto' }}>
        {stages.map((s, i) => {
          const isCurrent = i === currentIdx
          const isDone = currentIdx == null
            ? s.status === 'SUCCESS' || s.status === 'FAILED'
            : i < (currentIdx ?? 0)
          const isWarn = s.status === 'FAILED' && !animated
          const isPending = currentIdx != null && i > (currentIdx ?? 0)

          const dotColor = isWarn
            ? TT.hitl.solid
            : (isDone || (currentIdx != null && isCurrent)) ? TT.primary : TT.subtle
          const dotBg = isWarn ? TT.hitl.bg : isDone ? TT.primarySoft : '#F3F4F6'

          const lineColor = isDone ? TT.primary : TT.border
          const timeLabel = animated && isCurrent
            ? 'procesando…'
            : isPending
            ? 'pendiente'
            : s.duration_ms > 0
            ? `${s.duration_ms} ms`
            : '—'

          return (
            <div key={s.name} style={{ display: 'flex', alignItems: 'stretch', gap: 0, minWidth: 0 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '4px 0', minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 24, height: 24, borderRadius: 999,
                    background: dotBg, color: dotColor,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <DotContent status={s.status} animated={animated} isCurrent={isCurrent} index={i} />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    <div style={{
                      fontSize: 13, fontWeight: 600, color: isPending ? TT.muted : TT.fg, whiteSpace: 'nowrap',
                    }}>
                      {STAGE_LABELS[s.name] ?? s.name}
                    </div>
                    <div style={{
                      fontSize: 11, color: TT.muted, fontFamily: 'monospace', whiteSpace: 'nowrap',
                    }}>
                      {timeLabel}
                    </div>
                  </div>
                </div>
              </div>
              {i < stages.length - 1 && (
                <div style={{
                  flex: 1, alignSelf: 'center', minWidth: 24,
                  height: 1, background: lineColor, margin: '0 12px',
                }} />
              )}
            </div>
          )
        })}
      </div>
      <style>{`@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 1 } 50% { transform: scale(.6); opacity: .6 } }`}</style>
    </>
  )
}
