"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { RoutingBadge } from "@/components/routing-badge"
import type { RoutingDecision } from "@/lib/mock-data"
import { Send, UserCheck, RotateCcw, Eye, XCircle, FileCheck } from "lucide-react"

interface RoutingDecisionPanelProps {
  routing: RoutingDecision
  reason?: string
}

const routingReasons: Record<RoutingDecision, string> = {
  AUTO_APPROVE: "Documento procesado con alta confianza. Todos los campos críticos validados correctamente.",
  HITL_STANDARD: "Se requiere revisión manual debido a confianza media en algunos campos.",
  HITL_PRIORITY: "Revisión prioritaria requerida. Confianza baja en campos críticos.",
  AUTO_REJECT: "Documento rechazado automáticamente debido a errores críticos o campos ilegibles.",
}

const routingColors: Record<RoutingDecision, { bg: string; border: string }> = {
  AUTO_APPROVE: { bg: "bg-emerald-50", border: "border-emerald-200" },
  HITL_STANDARD: { bg: "bg-yellow-50", border: "border-yellow-200" },
  HITL_PRIORITY: { bg: "bg-orange-50", border: "border-orange-200" },
  AUTO_REJECT: { bg: "bg-red-50", border: "border-red-200" },
}

export function RoutingDecisionPanel({ routing, reason }: RoutingDecisionPanelProps) {
  const colors = routingColors[routing]
  const displayReason = reason || routingReasons[routing]

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
        <h3 className="font-semibold text-slate-900">Decisión de Enrutamiento</h3>
      </div>
      
      <div className={cn("p-6", colors.bg)}>
        <div className="text-center mb-6">
          <RoutingBadge routing={routing} size="lg" />
          <p className="mt-4 text-sm text-slate-600 max-w-md mx-auto">
            {displayReason}
          </p>
        </div>

        {/* Action buttons based on routing */}
        <div className="flex justify-center gap-3">
          {routing === "AUTO_APPROVE" && (
            <>
              <Button className="bg-indigo-600 hover:bg-indigo-700">
                <Send className="mr-2 h-4 w-4" />
                Enviar a SAP
              </Button>
              <Button variant="outline">
                <UserCheck className="mr-2 h-4 w-4" />
                Solicitar revisión manual
              </Button>
            </>
          )}

          {(routing === "HITL_STANDARD" || routing === "HITL_PRIORITY") && (
            <>
              <Button className="bg-emerald-600 hover:bg-emerald-700">
                <FileCheck className="mr-2 h-4 w-4" />
                Aprobar y enviar a SAP
              </Button>
              <Button variant="outline" className="text-red-600 hover:text-red-700 hover:bg-red-50">
                <XCircle className="mr-2 h-4 w-4" />
                Rechazar documento
              </Button>
            </>
          )}

          {routing === "AUTO_REJECT" && (
            <>
              <Button variant="outline">
                <Eye className="mr-2 h-4 w-4" />
                Ver motivo
              </Button>
              <Button className="bg-indigo-600 hover:bg-indigo-700">
                <RotateCcw className="mr-2 h-4 w-4" />
                Reenviar para reprocesar
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
