"use client"

import { cn } from "@/lib/utils"
import { ConfidenceBadge } from "@/components/confidence-badge"
import type { PipelineStage } from "@/lib/mock-data"
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts"

interface ModelMetricsPanelProps {
  stages: PipelineStage[]
  confidenceScore: number
}

export function ModelMetricsPanel({ stages, confidenceScore }: ModelMetricsPanelProps) {
  const usedModels = ["DocAI", "Tesseract"]
  const skippedModels = ["Vertex"]
  
  const totalDuration = stages.reduce((sum, s) => sum + s.duration_ms, 0) / 1000

  // Prepare data for the bar chart
  const chartData = stages
    .filter(s => s.duration_ms > 0)
    .map(s => ({
      name: s.name === "CLASSIFIED" ? "Clasificación" :
            s.name === "EXTRACTED" ? "Extracción" :
            s.name === "VALIDATED" ? "Validación" :
            s.name === "ROUTED" ? "Conciliación" :
            s.name,
      duration: s.duration_ms,
    }))

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
        <h3 className="font-semibold text-slate-900">Métricas de Modelos</h3>
      </div>
      
      <div className="p-6">
        {/* Metrics cards row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500 mb-2">Modelos usados</p>
            <div className="flex flex-wrap gap-2">
              {usedModels.map((model) => (
                <span 
                  key={model}
                  className={cn(
                    "rounded-md px-2 py-1 text-sm font-medium",
                    model === "DocAI" && "bg-blue-100 text-blue-700",
                    model === "Tesseract" && "bg-purple-100 text-purple-700",
                    model === "Vertex" && "bg-teal-100 text-teal-700"
                  )}
                >
                  {model}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500 mb-2">Modelos saltados</p>
            <div className="flex flex-wrap gap-2">
              {skippedModels.map((model) => (
                <span 
                  key={model}
                  className="rounded-md bg-slate-100 px-2 py-1 text-sm font-medium text-slate-500"
                >
                  {model}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500 mb-2">Duración total</p>
            <p className="text-2xl font-bold text-slate-900">{totalDuration.toFixed(1)}s</p>
          </div>

          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm text-slate-500 mb-2">Confidence global</p>
            <ConfidenceBadge confidence={confidenceScore} size="lg" />
          </div>
        </div>

        {/* Duration bar chart */}
        <div>
          <p className="text-sm font-medium text-slate-700 mb-3">Duración por etapa (ms)</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <XAxis type="number" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false}
                  width={100}
                />
                <Tooltip 
                  formatter={(value: number) => [`${value}ms`, "Duración"]}
                  contentStyle={{ 
                    fontSize: 12, 
                    borderRadius: 8, 
                    border: "1px solid #e2e8f0" 
                  }}
                />
                <Bar 
                  dataKey="duration" 
                  fill="#4f46e5" 
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
