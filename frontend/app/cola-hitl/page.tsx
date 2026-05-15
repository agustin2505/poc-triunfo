"use client"

import { useEffect, useState, useMemo } from "react"
import Link from "next/link"
import { RefreshCw, Search, Inbox, FileText, Image as ImageIcon } from "lucide-react"
import { TT } from "@/lib/theme"
import { RoutingBadge } from "@/components/routing-badge"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { listDocuments, adaptListItem } from "@/lib/api"
import type { ProcessedDocument } from "@/lib/mock-data"

type TabId = 'todos' | 'HITL_PRIORITY' | 'HITL_STANDARD'

export default function ColaHITLPage() {
  const [all, setAll] = useState<ProcessedDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabId>('todos')
  const [search, setSearch] = useState('')
  const [providerFilter, setProviderFilter] = useState('Todos')

  const load = () => {
    setLoading(true)
    setError(null)
    listDocuments(200)
      .then(data => {
        const hitl = data.documents
          .map(adaptListItem)
          .filter(d => d.routing === 'HITL_STANDARD' || d.routing === 'HITL_PRIORITY')
        setAll(hitl)
        setLoading(false)
      })
      .catch(err => { setError(err.message); setLoading(false) })
  }

  useEffect(() => { load() }, [])

  const providers = useMemo(() => {
    const set = new Set(all.map(d => d.provider).filter(Boolean))
    return ['Todos', ...Array.from(set)]
  }, [all])

  const filtered = useMemo(() => {
    return all.filter(d => {
      if (tab !== 'todos' && d.routing !== tab) return false
      if (providerFilter !== 'Todos' && d.provider !== providerFilter) return false
      if (search) {
        const q = search.toLowerCase()
        if (!d.filename.toLowerCase().includes(q) && !d.document_id.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [all, tab, search, providerFilter])

  const counts = {
    todos: all.length,
    HITL_PRIORITY: all.filter(d => d.routing === 'HITL_PRIORITY').length,
    HITL_STANDARD: all.filter(d => d.routing === 'HITL_STANDARD').length,
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: 'todos',         label: 'Todos' },
    { id: 'HITL_PRIORITY', label: 'Prioritarios' },
    { id: 'HITL_STANDARD', label: 'Estándar' },
  ]

  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '24px 32px 64px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-.01em', margin: 0, color: TT.fg }}>Cola HITL</h1>
          <p style={{ fontSize: 15, color: TT.muted, marginTop: 6, lineHeight: 1.55 }}>
            Documentos pendientes de revisión humana, ordenados por prioridad.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            height: 38, padding: '0 14px', fontSize: 14, fontWeight: 500, borderRadius: 8,
            background: 'transparent', color: TT.fg, border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          <RefreshCw size={15} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          Actualizar
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, borderBottom: `1px solid ${TT.border}` }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding: '10px 14px', fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: tab === t.id ? TT.primary : TT.muted,
            borderBottom: tab === t.id ? `2px solid ${TT.primary}` : '2px solid transparent',
            marginBottom: -1, display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            {t.label}
            <span style={{
              background: tab === t.id ? TT.primarySoft : '#F3F4F6',
              color: tab === t.id ? TT.primaryHover : TT.muted,
              fontSize: 11, fontWeight: 600, padding: '1px 6px', borderRadius: 999,
            }}>
              {counts[t.id]}
            </span>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div style={{
        background: TT.surface, border: `1px solid ${TT.border}`, borderTop: 'none',
        padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{ position: 'relative' }}>
          <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: TT.subtle, pointerEvents: 'none' }}>
            <Search size={14} />
          </span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por nombre o doc_id…"
            style={{
              height: 34, padding: '0 12px 0 32px', fontSize: 13, width: 280, fontFamily: 'inherit',
              background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 8,
              outline: 'none', color: TT.fg,
            }}
          />
        </div>
        <select
          value={providerFilter}
          onChange={e => setProviderFilter(e.target.value)}
          style={{
            height: 34, padding: '0 28px 0 12px', fontSize: 13, fontFamily: 'inherit',
            background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 8,
            color: TT.fg, appearance: 'none', cursor: 'pointer',
            backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2'><polyline points='6 9 12 15 18 9'/></svg>")`,
            backgroundRepeat: 'no-repeat', backgroundPosition: 'right 8px center',
          }}
        >
          {providers.map(p => <option key={p}>{p}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: 13, color: TT.muted }}>{filtered.length} en cola</div>
      </div>

      {/* Table */}
      <div style={{
        background: TT.surface, border: `1px solid ${TT.border}`,
        borderTop: 'none', borderRadius: '0 0 10px 10px', overflow: 'hidden',
      }}>
        {error ? (
          <div style={{ padding: 48, textAlign: 'center', color: TT.reject.fg, fontSize: 14 }}>{error}</div>
        ) : loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: TT.muted, fontSize: 14 }}>Cargando cola…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: TT.background }}>
                {['Documento', 'Proveedor', 'Routing', 'Score', 'Acción'].map((h, i) => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '10px 16px', fontSize: 11, fontWeight: 600,
                    color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em',
                    borderBottom: `1px solid ${TT.border}`,
                    width: i === 0 ? undefined : i === 1 ? 160 : i === 2 ? 180 : i === 3 ? 160 : 140,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: 48, textAlign: 'center', color: TT.muted }}>
                    <div style={{ width: 40, height: 40, margin: '0 auto 12px', color: TT.subtle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Inbox size={40} />
                    </div>
                    <div style={{ fontSize: 14 }}>No hay documentos que coincidan con el filtro.</div>
                  </td>
                </tr>
              ) : (
                filtered.map((d, i) => (
                  <QueueRow key={d.document_id} doc={d} idx={i} />
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
      <style>{`@keyframes spin { 100% { transform: rotate(360deg) } }`}</style>
    </div>
  )
}

function QueueRow({ doc, idx }: { doc: ProcessedDocument; idx: number }) {
  const [hover, setHover] = useState(false)
  const isPdf = doc.filename?.toLowerCase().endsWith('.pdf') ?? true

  return (
    <tr
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        cursor: 'pointer', background: hover ? TT.background : TT.surface,
        borderTop: idx === 0 ? 'none' : `1px solid ${TT.divider}`,
      }}
    >
      <td style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 40, borderRadius: 6, background: TT.accentSoft, color: TT.accent,
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            {isPdf ? <FileText size={18} /> : <ImageIcon size={18} />}
          </div>
          <div>
            <div style={{ fontWeight: 500, color: TT.fg }}>{doc.filename}</div>
            <div style={{ fontSize: 11, color: TT.muted, fontFamily: 'monospace', marginTop: 2 }}>{doc.document_id}</div>
          </div>
        </div>
      </td>
      <td style={{ padding: '14px 16px', color: TT.fg }}>{doc.provider}</td>
      <td style={{ padding: '14px 16px' }}>
        <RoutingBadge routing={doc.routing} size="sm" />
      </td>
      <td style={{ padding: '14px 16px' }}>
        <ConfidenceBadge confidence={doc.confidence_score} />
      </td>
      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
        <Link href={`/resultado/${doc.document_id}`} style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          height: 32, padding: '0 12px', fontSize: 13, fontWeight: 500, borderRadius: 8,
          background: 'transparent', color: TT.fg, border: `1px solid ${TT.border}`,
          textDecoration: 'none', transition: 'all 150ms ease',
        }}>
          Revisar →
        </Link>
      </td>
    </tr>
  )
}
