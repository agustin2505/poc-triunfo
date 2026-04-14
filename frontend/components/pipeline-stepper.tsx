"use client"

import { Check, X, Loader2, Circle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { PipelineStage, StageStatus } from "@/lib/mock-data"

interface PipelineStepperProps {
  stages: PipelineStage[]
  provider?: string
  category?: string
}

const stageLabels: Record<string, string> = {
  INGESTED: "Ingresado",
  CLASSIFIED: "Clasificado",
  PROCESSING: "Procesando",
  EXTRACTED: "Extraído",
  VALIDATED: "Validado",
  ROUTED: "Enrutado"
}

export function PipelineStepper({ stages, provider, category }: PipelineStepperProps) {
  const getStatusIcon = (status: StageStatus) => {
    switch (status) {
      case "SUCCESS":
        return <Check className="h-4 w-4" />
      case "FAILED":
        return <X className="h-4 w-4" />
      case "PROCESSING":
        return <Loader2 className="h-4 w-4 animate-spin" />
      case "SKIPPED":
        return <Circle className="h-4 w-4" />
      default:
        return <Circle className="h-4 w-4" />
    }
  }

  const getStatusColor = (status: StageStatus) => {
    switch (status) {
      case "SUCCESS":
        return "bg-emerald-500 text-white"
      case "FAILED":
        return "bg-red-500 text-white"
      case "PROCESSING":
        return "bg-indigo-500 text-white"
      case "SKIPPED":
        return "bg-slate-300 text-slate-600"
      default:
        return "bg-slate-200 text-slate-400"
    }
  }

  const getLineColor = (status: StageStatus) => {
    switch (status) {
      case "SUCCESS":
        return "bg-emerald-500"
      case "FAILED":
        return "bg-red-500"
      default:
        return "bg-slate-200"
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-0">
        {stages.map((stage, index) => (
          <div key={stage.name} className="relative">
            {/* Connector line */}
            {index < stages.length - 1 && (
              <div 
                className={cn(
                  "absolute left-[15px] top-[32px] h-8 w-0.5",
                  getLineColor(stage.status)
                )} 
              />
            )}
            
            <div className="flex items-center gap-4 py-2">
              {/* Status icon */}
              <div className={cn(
                "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full",
                getStatusColor(stage.status)
              )}>
                {getStatusIcon(stage.status)}
              </div>
              
              {/* Stage info */}
              <div className="flex flex-1 items-center justify-between">
                <span className={cn(
                  "font-medium",
                  stage.status === "PENDING" ? "text-slate-400" : "text-slate-700"
                )}>
                  {stageLabels[stage.name] || stage.name}
                </span>
                
                {stage.status === "SUCCESS" && stage.duration_ms > 0 && (
                  <span className="text-sm text-slate-500">
                    {stage.duration_ms}ms
                  </span>
                )}
                {stage.status === "PROCESSING" && (
                  <span className="text-sm text-indigo-600">
                    Procesando...
                  </span>
                )}
                {stage.status === "SKIPPED" && (
                  <span className="text-sm text-slate-400">
                    Saltado
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Provider and category info */}
      {provider && (
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div>
            <p className="text-sm text-slate-500">Proveedor detectado</p>
            <p className="font-semibold text-slate-900">{provider}</p>
          </div>
          {category && (
            <>
              <div className="h-8 w-px bg-slate-200" />
              <div>
                <p className="text-sm text-slate-500">Categoría</p>
                <span className="inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-sm font-medium text-indigo-800">
                  {category}
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
