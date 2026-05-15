"use client"

import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { TT, ROUTING_META } from "@/lib/theme"
import { RoutingBadge } from "@/components/routing-badge"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { getMetrics, type BackendMetrics } from "@/lib/api"

const ROUTING_ORDER = ['AUTO_APPROVE', 'HITL_STANDARD', 'HITL_PRIORITY', 'AUTO_REJECT'] as const

function KpiCard({ label, value, sub, subColor }: {
  label: string; value: string; sub?: string; subColor?: string
}) {
  return (
    <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20, flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 12, color: TT.muted, fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-.02em', color: TT.fg, marginTop: 8, fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: subColor ?? TT.muted, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

export default function MetricasPage() {
  const [metrics, setMetrics] = useState<BackendMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMetrics()
      .then(data => { setMetrics(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const total = metrics?.total_documents ?? 0
  const routing = metrics?.routing_distribution ?? {}
  const totalOrOne = total || 1

  const stpRate = ((routing.AUTO_APPROVE ?? 0) / totalOrOne * 100).toFixed(1)
  const latencyP95 = metrics ? (metrics.latency_p95_ms / 1000).toFixed(2) : '—'
  const avgConfidence = metrics?.agent_stats?.length
    ? (metrics.agent_stats.reduce((s, a) => s + a.avg_confidence, 0) / metrics.agent_stats.length).toFixed(2)
    : '—'

  const confidenceDist = metrics?.confidence_distribution ?? {}
  const confidenceBands = [
    { band: 'high',     label: '≥ 0.88',    color: TT.approve.solid, bg: TT.approve.bg },
    { band: 'mid',      label: '0.70–0.88',  color: TT.hitl.solid,   bg: TT.hitl.bg },
    { band: 'low',      label: '0.40–0.70',  color: TT.priority.solid, bg: TT.priority.bg },
    { band: 'critical', label: '< 0.40',     color: TT.reject.solid,  bg: TT.reject.bg },
  ]

  const agentStats = metrics?.agent_stats ?? []

  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '24px 32px 64px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-.01em', margin: 0, color: TT.fg }}>
            Métricas del pipeline
          </h1>
          <p style={{ fontSize: 15, color: TT.muted, marginTop: 6, lineHeight: 1.55 }}>
            {loading
              ? 'Cargando datos...'
              : metrics
              ? `${metrics.total_documents} documentos procesados en total`
              : 'Sin datos disponibles'}
          </p>
        </div>
        {loading && <Loader2 size={20} className="animate-spin" style={{ color: TT.muted }} />}
      </div>

      {/* KPI cards */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <KpiCard label="Documentos procesados" value={String(total)} />
        <KpiCard label="Tasa de auto-aprobación" value={`${stpRate}%`} sub="(STP rate)" />
        <KpiCard label="Latencia P95" value={metrics ? `${latencyP95} s` : '—'} />
        <KpiCard label="Confidence promedio" value={avgConfidence} sub="por agente" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Routing distribution */}
        <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 16 }}>
            Distribución de routing
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {ROUTING_ORDER.map(r => {
              const count = routing[r] ?? 0
              const pct = total > 0 ? Math.round((count / total) * 100) : 0
              const meta = ROUTING_META[r]
              const colors = TT[meta.tone]
              return (
                <div key={r}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <RoutingBadge routing={r as Parameters<typeof RoutingBadge>[0]['routing']} size="sm" />
                    <span style={{ fontFamily: 'monospace', fontSize: 13, color: TT.fg, fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>
                      {count} · {pct}%
                    </span>
                  </div>
                  <div style={{ height: 6, background: TT.background, borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: colors.solid, transition: 'width 400ms ease' }} />
                  </div>
                </div>
              )
            })}
            {total === 0 && !loading && (
              <div style={{ fontSize: 13, color: TT.muted, textAlign: 'center', padding: '16px 0' }}>Sin documentos procesados</div>
            )}
          </div>
        </div>

        {/* Confidence distribution */}
        <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 16 }}>
            Distribución de confidence
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {confidenceBands.map(({ band, label, color, bg }, i) => {
                const bandData = confidenceDist[band] ?? {}
                const count = Object.values(bandData).reduce((s, v) => s + v, 0)
                const pct = total > 0 ? Math.round((count / total) * 100) : 0
                return (
                  <tr key={band} style={{ borderTop: i === 0 ? 'none' : `1px solid ${TT.divider}` }}>
                    <td style={{ padding: '10px 0', width: 130 }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 10, height: 10, borderRadius: 3, background: color }} />
                        <span style={{ fontWeight: 500, color: TT.fg }}>{label}</span>
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ height: 6, background: bg, borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width 400ms ease' }} />
                      </div>
                    </td>
                    <td style={{ padding: '10px 0 10px 12px', textAlign: 'right', fontFamily: 'monospace', color: TT.fg, fontWeight: 500, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                      {count} · {pct}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Agent stats table */}
      <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: `1px solid ${TT.border}`, fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em' }}>
          Estadísticas de agentes
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: TT.background }}>
              {['Agente', 'Invocaciones', 'Éxitos', 'Tasa éxito', 'Timeout', 'Dur. avg', 'Conf. avg'].map(h => (
                <th key={h} style={{
                  textAlign: h === 'Agente' ? 'left' : 'right', padding: '10px 16px',
                  fontSize: 11, fontWeight: 600, color: TT.muted, textTransform: 'uppercase',
                  letterSpacing: '.06em', borderBottom: `1px solid ${TT.border}`, whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agentStats.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: TT.muted }}>
                  {loading ? 'Cargando...' : 'Sin datos de agentes'}
                </td>
              </tr>
            )}
            {agentStats.map((agent, i) => {
              const agentColors: Record<string, { bg: string; fg: string }> = {
                DocAI:     { bg: '#DBEAFE', fg: '#1D4ED8' },
                Tesseract: { bg: '#F3E8FF', fg: '#7E22CE' },
                Vertex:    { bg: '#CCFBF1', fg: '#0F766E' },
              }
              const ac = agentColors[agent.name] ?? { bg: TT.background, fg: TT.fg }
              const successColor = agent.success_rate >= 0.95 ? TT.approve.fg : agent.success_rate >= 0.90 ? TT.hitl.fg : TT.reject.fg
              const confColor = agent.avg_confidence >= 0.88 ? TT.approve.fg : agent.avg_confidence >= 0.70 ? TT.hitl.fg : TT.reject.fg
              return (
                <tr key={agent.name} style={{ borderTop: i === 0 ? 'none' : `1px solid ${TT.divider}` }}>
                  <td style={{ padding: '14px 16px' }}>
                    <span style={{ background: ac.bg, color: ac.fg, fontSize: 12, fontWeight: 600, padding: '3px 10px', borderRadius: 6 }}>
                      {agent.name}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>{agent.invocations}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>{agent.successes}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: successColor, fontFamily: 'monospace' }}>
                    {(agent.success_rate * 100).toFixed(0)}%
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', color: TT.muted, fontFamily: 'monospace' }}>
                    {(agent.timeout_rate * 100).toFixed(1)}%
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>
                    {(agent.avg_duration_ms / 1000).toFixed(1)}s
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <ConfidenceBadge confidence={agent.avg_confidence} size="sm" />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
