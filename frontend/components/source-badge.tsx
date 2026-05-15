import type { FieldSource } from "@/lib/mock-data"

interface SourceBadgeProps {
  source: FieldSource
}

const SOURCE_CONFIG: Record<FieldSource, { label: string; bg: string; fg: string }> = {
  majority:  { label: 'Mayoría',   bg: '#EDE9FE', fg: '#5B21B6' },
  docai:     { label: 'DocAI',     bg: '#DBEAFE', fg: '#1D4ED8' },
  tesseract: { label: 'Tesseract', bg: '#F3E8FF', fg: '#7E22CE' },
  vertex:    { label: 'Vertex',    bg: '#CCFBF1', fg: '#0F766E' },
  missing:   { label: 'Faltante',  bg: '#F3F4F6', fg: '#6B7280' },
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const cfg = SOURCE_CONFIG[source] ?? SOURCE_CONFIG.missing
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      background: cfg.bg, color: cfg.fg,
      fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 6,
      whiteSpace: 'nowrap',
    }}>
      {cfg.label}
    </span>
  )
}
