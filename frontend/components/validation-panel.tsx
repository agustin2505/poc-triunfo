"use client"

import { Check, AlertTriangle, X } from "lucide-react"
import { TT } from "@/lib/theme"
import type { DocumentValidation } from "@/lib/mock-data"

interface ValidationPanelProps {
  validation: DocumentValidation
}

function StatusIcon({ type }: { type: 'ok' | 'warn' | 'error' }) {
  if (type === 'ok')    return <Check    size={15} style={{ color: TT.approve.solid }} />
  if (type === 'warn')  return <AlertTriangle size={15} style={{ color: TT.hitl.solid }} />
  return <X size={15} style={{ color: TT.reject.solid }} />
}

export function ValidationPanel({ validation }: ValidationPanelProps) {
  const { errors, warnings } = validation
  const okCount = errors.length === 0 && warnings.length === 0 ? 1 : 0

  return (
    <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em' }}>
          Validaciones
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {okCount > 0 && (
            <span style={{ background: TT.approve.bg, color: TT.approve.fg, fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999 }}>
              OK
            </span>
          )}
          {warnings.length > 0 && (
            <span style={{ background: TT.hitl.bg, color: TT.hitl.fg, fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999 }}>
              {warnings.length} aviso{warnings.length > 1 ? 's' : ''}
            </span>
          )}
          {errors.length > 0 && (
            <span style={{ background: TT.reject.bg, color: TT.reject.fg, fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999 }}>
              {errors.length} error{errors.length > 1 ? 'es' : ''}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {errors.map((msg, i) => (
          <div key={`e-${i}`} style={{
            display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 10px',
            borderRadius: 6, background: TT.reject.bg,
          }}>
            <StatusIcon type="error" />
            <span style={{ fontSize: 13, color: TT.fg, lineHeight: 1.5 }}>{msg}</span>
          </div>
        ))}

        {warnings.map((msg, i) => (
          <div key={`w-${i}`} style={{
            display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 10px',
            borderRadius: 6, background: TT.hitl.bg,
          }}>
            <StatusIcon type="warn" />
            <span style={{ fontSize: 13, color: TT.fg, lineHeight: 1.5 }}>{msg}</span>
          </div>
        ))}

        {errors.length === 0 && warnings.length === 0 && (
          <div style={{
            display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 10px',
            borderRadius: 6, background: '#F9FAFB',
          }}>
            <StatusIcon type="ok" />
            <span style={{ fontSize: 13, color: TT.muted }}>Sin errores ni advertencias</span>
          </div>
        )}
      </div>
    </div>
  )
}
