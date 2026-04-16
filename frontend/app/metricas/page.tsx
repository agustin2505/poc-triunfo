"use client"

import { useEffect, useState } from "react"
import { FileText, Zap, Clock, AlertTriangle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { getMetrics, type BackendMetrics } from "@/lib/api"
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Legend,
} from "recharts"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const routingColors: Record<string, string> = {
  AUTO_APPROVE: "#10b981",
  HITL_STANDARD: "#eab308",
  HITL_PRIORITY: "#f97316",
  AUTO_REJECT: "#ef4444",
}

const routingLabels: Record<string, string> = {
  AUTO_APPROVE: "Auto Aprobado",
  HITL_STANDARD: "HITL Estándar",
  HITL_PRIORITY: "HITL Prioritario",
  AUTO_REJECT: "Auto Rechazado",
}

interface MetricCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: { value: number; positive: boolean }
  valueColor?: string
}

function MetricCard({ title, value, icon: Icon, trend, valueColor }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className={cn("mt-2 text-3xl font-bold", valueColor || "text-slate-900")}>
            {value}
          </p>
          {trend && (
            <p className={cn("mt-1 text-sm", trend.positive ? "text-emerald-600" : "text-red-600")}>
              {trend.positive ? "+" : ""}{trend.value}% vs. ayer
            </p>
          )}
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100">
          <Icon className="h-6 w-6 text-slate-600" />
        </div>
      </div>
    </div>
  )
}

const MOCK_AGENT_STATS = [
  { name: "DocAI", invocations: 0, successes: 0, success_rate: 0, timeout_rate: 0, avg_duration_ms: 0, avg_confidence: 0 },
  { name: "Tesseract", invocations: 0, successes: 0, success_rate: 0, timeout_rate: 0, avg_duration_ms: 0, avg_confidence: 0 },
  { name: "Vertex", invocations: 0, successes: 0, success_rate: 0, timeout_rate: 0, avg_duration_ms: 0, avg_confidence: 0 },
]

export default function MetricasPage() {
  const [metrics, setMetrics] = useState<BackendMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMetrics()
      .then((data) => {
        setMetrics(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const routing = metrics?.routing_distribution ?? { AUTO_APPROVE: 0, HITL_STANDARD: 0, HITL_PRIORITY: 0, AUTO_REJECT: 0 }
  const total = metrics?.total_documents ?? 0
  const totalOrOne = total || 1
  const stpRate = (routing.AUTO_APPROVE ?? 0) / totalOrOne
  const errorRate = (routing.AUTO_REJECT ?? 0) / totalOrOne
  const latencyP95 = metrics ? (metrics.latency_p95_ms / 1000).toFixed(1) : "—"
  const agentStats = metrics?.agent_stats ?? MOCK_AGENT_STATS

  const pieData = Object.entries(routing).map(([key, value]) => ({
    name: routingLabels[key] || key,
    value,
    color: routingColors[key] || "#94a3b8",
  }))

  const confidenceDist = metrics?.confidence_distribution ?? {}
  const confidenceData = Object.entries(confidenceDist).map(([range, agents]) => ({
    range,
    DocAI: agents.agent_a ?? 0,
    Tesseract: agents.agent_b ?? 0,
    Vertex: agents.agent_c ?? 0,
  }))

  return (
    <div className="min-h-[calc(100vh-4rem)] p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Dashboard de Métricas</h1>
            <p className="text-slate-500">
              {loading
                ? "Cargando datos..."
                : live
                ? `${live.total} documentos procesados en total`
                : "Métricas de procesamiento del día actual"}
            </p>
          </div>
          {loading && <Loader2 className="h-5 w-5 animate-spin text-slate-400" />}
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <MetricCard
            title="Docs procesados"
            value={total}
            icon={FileText}
          />
          <MetricCard
            title="STP Rate"
            value={`${(stpRate * 100).toFixed(0)}%`}
            icon={Zap}
            valueColor="text-emerald-600"
          />
          <MetricCard
            title="Latencia P95"
            value={`${latencyP95}s`}
            icon={Clock}
          />
          <MetricCard
            title="Error Rate"
            value={`${(errorRate * 100).toFixed(1)}%`}
            icon={AlertTriangle}
            valueColor={errorRate > 0.05 ? "text-red-600" : "text-slate-900"}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h3 className="mb-4 font-semibold text-slate-900">Distribución de Routing</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [value, "Documentos"]}
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {pieData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                  <span className="text-sm text-slate-600">
                    {entry.name} ({entry.value})
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
              <h3 className="font-semibold text-slate-900">Tabla de Agentes</h3>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Agente</TableHead>
                    <TableHead className="text-right">Invocaciones</TableHead>
                    <TableHead className="text-right">Éxitos</TableHead>
                    <TableHead className="text-right">Tasa éxito</TableHead>
                    <TableHead className="text-right">Timeout</TableHead>
                    <TableHead className="text-right">Dur. avg</TableHead>
                    <TableHead className="text-right">Conf. avg</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {agentStats.map((agent) => (
                    <TableRow key={agent.name}>
                      <TableCell>
                        <span className={cn(
                          "rounded-md px-2 py-1 text-sm font-medium",
                          agent.name === "DocAI" && "bg-blue-100 text-blue-700",
                          agent.name === "Tesseract" && "bg-purple-100 text-purple-700",
                          agent.name === "Vertex" && "bg-teal-100 text-teal-700"
                        )}>
                          {agent.name}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">{agent.invocations}</TableCell>
                      <TableCell className="text-right">{agent.successes}</TableCell>
                      <TableCell className="text-right">
                        <span className={cn(
                          "font-medium",
                          agent.success_rate >= 0.95 ? "text-emerald-600" :
                          agent.success_rate >= 0.90 ? "text-yellow-600" : "text-red-600"
                        )}>
                          {(agent.success_rate * 100).toFixed(0)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-slate-500">
                        {(agent.timeout_rate * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-right">
                        {(agent.avg_duration_ms / 1000).toFixed(1)}s
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={cn(
                          "font-medium",
                          agent.avg_confidence >= 0.88 ? "text-emerald-600" :
                          agent.avg_confidence >= 0.70 ? "text-yellow-600" : "text-red-600"
                        )}>
                          {agent.avg_confidence.toFixed(2)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>

        {/* Confidence distribution */}
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 font-semibold text-slate-900">
            Distribución de Confidence por Agente
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={confidenceData}>
                <XAxis dataKey="range" fontSize={12} tickLine={false} />
                <YAxis fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                <Legend />
                <Bar dataKey="DocAI" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Tesseract" fill="#a855f7" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Vertex" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
