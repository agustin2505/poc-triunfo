"use client"

import { CheckCircle2, AlertTriangle, XCircle, MinusCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DocumentValidation } from "@/lib/mock-data"

interface ValidationPanelProps {
  validation: DocumentValidation
}

export function ValidationPanel({ validation }: ValidationPanelProps) {
  const { errors, warnings } = validation
  const hasErrors = errors.length > 0
  const hasWarnings = warnings.length > 0
  
  const status = hasErrors ? "FAILED" : hasWarnings ? "WARNINGS" : "PASSED"
  
  const statusConfig = {
    PASSED: {
      icon: CheckCircle2,
      label: "Validación exitosa",
      bgColor: "bg-emerald-50",
      textColor: "text-emerald-700",
      borderColor: "border-emerald-200",
      iconColor: "text-emerald-500",
    },
    WARNINGS: {
      icon: AlertTriangle,
      label: "Validación con advertencias",
      bgColor: "bg-yellow-50",
      textColor: "text-yellow-700",
      borderColor: "border-yellow-200",
      iconColor: "text-yellow-500",
    },
    FAILED: {
      icon: XCircle,
      label: "Validación fallida",
      bgColor: "bg-red-50",
      textColor: "text-red-700",
      borderColor: "border-red-200",
      iconColor: "text-red-500",
    },
  }

  const config = statusConfig[status]
  const StatusIcon = config.icon

  // Extract missing fields from warnings
  const missingFieldWarnings = warnings.filter(w => w.includes("no extraído"))
  const otherWarnings = warnings.filter(w => !w.includes("no extraído"))

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
        <h3 className="font-semibold text-slate-900">Validaciones</h3>
      </div>
      
      <div className="p-6">
        {/* Status header */}
        <div className={cn(
          "flex items-center gap-3 rounded-lg border p-4 mb-4",
          config.bgColor,
          config.borderColor
        )}>
          <StatusIcon className={cn("h-6 w-6", config.iconColor)} />
          <span className={cn("font-semibold", config.textColor)}>
            {config.label}
          </span>
        </div>

        <div className="space-y-3">
          {/* Errors */}
          {errors.map((error, index) => (
            <div 
              key={`error-${index}`}
              className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3"
            >
              <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          ))}

          {/* Other warnings */}
          {otherWarnings.map((warning, index) => (
            <div 
              key={`warning-${index}`}
              className="flex items-start gap-3 rounded-lg border border-yellow-200 bg-yellow-50 p-3"
            >
              <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-500" />
              <span className="text-sm text-yellow-700">{warning}</span>
            </div>
          ))}

          {/* Missing fields */}
          {missingFieldWarnings.map((warning, index) => (
            <div 
              key={`missing-${index}`}
              className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3"
            >
              <MinusCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-slate-400" />
              <span className="text-sm text-slate-600">{warning}</span>
            </div>
          ))}

          {/* All good message */}
          {!hasErrors && !hasWarnings && (
            <p className="text-center text-sm text-slate-500 py-4">
              No se encontraron errores ni advertencias
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
