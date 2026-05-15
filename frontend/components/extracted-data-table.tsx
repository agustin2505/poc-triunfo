"use client"

import { useState, useMemo, Fragment } from "react"
import { ChevronRight, Check, AlertTriangle, X, ArrowUp, ArrowDown, MoreHorizontal } from "lucide-react"
import { TT, FIELD_LABELS, confBand, confStatus } from "@/lib/theme"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { SourceBadge } from "@/components/source-badge"
import type { ExtractedField, RoutingDecision } from "@/lib/mock-data"

interface ExtractedDataTableProps {
  fields: Record<string, ExtractedField>
  routing: RoutingDecision
}

type SortCol = 'label' | 'value' | 'confidence' | null
type SortDir = 'asc' | 'desc'

const AGENT_CONFIG: Record<string, { label: string; bg: string; fg: string }> = {
  agentA: { label: 'DocAI',     bg: '#DBEAFE', fg: '#1D4ED8' },
  agentB: { label: 'Tesseract', bg: '#F3E8FF', fg: '#7E22CE' },
  agentC: { label: 'Vertex',    bg: '#CCFBF1', fg: '#0F766E' },
}

function StatusIcon({ status }: { status: 'ok' | 'warn' | 'error' }) {
  if (status === 'ok')    return <Check         size={15} style={{ color: TT.approve.solid }} />
  if (status === 'warn')  return <AlertTriangle size={15} style={{ color: TT.hitl.solid }} />
  return <X size={15} style={{ color: TT.reject.solid }} />
}

function SortIndicator({ col, active, dir }: { col: string; active: boolean; dir: SortDir }) {
  if (!active) return null
  return dir === 'asc' ? <ArrowUp size={12} style={{ color: TT.primary }} /> : <ArrowDown size={12} style={{ color: TT.primary }} />
}

function formatValue(key: string, val: string | number | null): string {
  if (val === null || val === undefined) return '—'
  return String(val)
}

export function ExtractedDataTable({ fields, routing }: ExtractedDataTableProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [sort, setSort] = useState<{ col: SortCol; dir: SortDir }>({ col: null, dir: 'asc' })

  const toggle = (k: string) => setExpanded(s => {
    const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n
  })

  const toggleSort = (col: SortCol) => setSort(s =>
    s.col === col ? { col, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { col, dir: 'asc' }
  )

  const entries = useMemo(() => {
    const list = Object.entries(fields)
    if (!sort.col) return list
    return [...list].sort(([ak, av], [bk, bv]) => {
      const { col, dir } = sort
      let a: string | number = 0, b: string | number = 0
      if (col === 'confidence') { a = av.confidence; b = bv.confidence }
      else if (col === 'label') { a = FIELD_LABELS[ak] ?? ak; b = FIELD_LABELS[bk] ?? bk }
      else if (col === 'value') { a = String(av.value ?? ''); b = String(bv.value ?? '') }
      if (typeof a === 'number') return dir === 'asc' ? a - (b as number) : (b as number) - a
      return dir === 'asc' ? String(a).localeCompare(String(b)) : String(b).localeCompare(String(a))
    })
  }, [fields, sort])

  const Th = ({ children, sortKey, w, right }: {
    children?: React.ReactNode; sortKey?: SortCol; w?: number; right?: boolean
  }) => (
    <th
      onClick={sortKey ? () => toggleSort(sortKey) : undefined}
      style={{
        textAlign: right ? 'right' : 'left', padding: '10px 14px', fontSize: 11, fontWeight: 600,
        color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em',
        borderBottom: `1px solid ${TT.border}`, background: TT.background,
        cursor: sortKey ? 'pointer' : 'default', userSelect: 'none', width: w, whiteSpace: 'nowrap',
      }}
    >
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        {children}
        {sortKey && <SortIndicator col={sortKey} active={sort.col === sortKey} dir={sort.dir} />}
      </span>
    </th>
  )

  return (
    <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 10, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'inherit' }}>
        <thead>
          <tr>
            <Th w={32} />
            <Th sortKey="label" w={180}>Campo</Th>
            <Th sortKey="value">Valor</Th>
            <Th sortKey="confidence" w={160}>Confidence</Th>
            <Th w={120}>Fuente</Th>
            <Th w={110}>Estado</Th>
            <Th w={32} right />
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, field]) => {
            const open = expanded.has(key)
            const status = confStatus(field.confidence)
            const isCritical = field.confidence < 0.40
            const label = FIELD_LABELS[key] ?? key

            const agentRows = (['agentA', 'agentB', 'agentC'] as const)
              .map(aKey => ({ aKey, data: field[aKey] }))
              .filter(({ data }) => data !== undefined)

            return (
              <Fragment key={key}>
                <tr
                  onClick={() => toggle(key)}
                  style={{
                    borderTop: `1px solid ${TT.divider}`,
                    background: open ? TT.background : TT.surface,
                    cursor: 'pointer',
                    borderLeft: isCritical ? `3px solid ${TT.reject.solid}` : '3px solid transparent',
                  }}
                  onMouseEnter={e => { if (!open) (e.currentTarget as HTMLTableRowElement).style.background = TT.background }}
                  onMouseLeave={e => { if (!open) (e.currentTarget as HTMLTableRowElement).style.background = TT.surface }}
                >
                  <td style={{ padding: '10px 8px 10px 14px', color: TT.subtle }}>
                    <span style={{ display: 'inline-flex', transform: open ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 150ms ease' }}>
                      <ChevronRight size={14} />
                    </span>
                  </td>
                  <td style={{ padding: '10px 14px', color: TT.fg, fontWeight: 500 }}>
                    {label}
                    <div style={{ fontSize: 11, color: TT.muted, fontFamily: 'monospace', marginTop: 2 }}>{key}</div>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: TT.fg, fontVariantNumeric: 'tabular-nums', fontWeight: 500, whiteSpace: 'nowrap' }}>
                    {formatValue(key, field.value)}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <ConfidenceBadge confidence={field.confidence} />
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <SourceBadge source={field.source} />
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <StatusIcon status={status} />
                      <span style={{
                        fontSize: 12, fontWeight: 500,
                        color: status === 'error' ? TT.reject.fg : status === 'warn' ? TT.hitl.fg : TT.muted,
                      }}>
                        {status === 'ok' ? 'Válido' : status === 'warn' ? 'Revisar' : 'Crítico'}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px', color: TT.subtle, textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                    <MoreHorizontal size={16} />
                  </td>
                </tr>

                {open && (
                  <tr style={{ background: TT.background }}>
                    <td colSpan={7} style={{ padding: '0 14px 16px 50px', borderTop: `1px solid ${TT.divider}` }}>
                      <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 8, padding: 14, marginTop: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10 }}>
                          Confidence por agente
                        </div>
                        {agentRows.length > 0 ? (
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                            <tbody>
                              {agentRows.map(({ aKey, data }, i) => {
                                if (!data) return null
                                const cfg = AGENT_CONFIG[aKey]
                                return (
                                  <tr key={aKey} style={{ borderTop: i === 0 ? 'none' : `1px solid ${TT.divider}` }}>
                                    <td style={{ padding: '8px 0', width: 110 }}>
                                      <span style={{
                                        display: 'inline-flex', alignItems: 'center',
                                        background: cfg.bg, color: cfg.fg,
                                        fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 6,
                                      }}>{cfg.label}</span>
                                    </td>
                                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: TT.fg, fontVariantNumeric: 'tabular-nums' }}>
                                      {data.value !== null && data.value !== undefined ? String(data.value) : <span style={{ color: TT.subtle }}>—</span>}
                                    </td>
                                    <td style={{ padding: '8px 12px', width: 180 }}>
                                      <ConfidenceBadge confidence={data.confidence} />
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        ) : (
                          <div style={{ fontSize: 13, color: TT.muted, padding: '8px 0' }}>Sin detalle por agente disponible</div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
          {entries.length === 0 && (
            <tr>
              <td colSpan={7} style={{ padding: 48, textAlign: 'center', color: TT.muted, fontSize: 14 }}>
                Sin campos extraídos
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
