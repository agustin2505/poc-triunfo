import { TT, confBand } from "@/lib/theme"

interface ConfidenceBadgeProps {
  confidence: number
  size?: "sm" | "md" | "lg"
}

export function ConfidenceBadge({ confidence, size = "md" }: ConfidenceBadgeProps) {
  if (confidence === 0) return <span style={{ color: TT.subtle }}>—</span>

  const band = confBand(confidence)
  const colors = TT[band]
  const barWidth = size === 'sm' ? 48 : size === 'lg' ? 80 : 56

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: barWidth, height: 6, borderRadius: 3, background: colors.bg, overflow: 'hidden', flexShrink: 0 }}>
        <div style={{ width: `${Math.round(confidence * 100)}%`, height: '100%', background: colors.solid, borderRadius: 3 }} />
      </div>
      <span style={{ fontFamily: 'monospace', fontSize: 12, color: colors.fg, fontWeight: 600, minWidth: 32, fontVariantNumeric: 'tabular-nums' }}>
        {confidence.toFixed(2)}
      </span>
    </div>
  )
}
