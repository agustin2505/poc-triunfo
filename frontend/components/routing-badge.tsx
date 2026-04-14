import { cn } from "@/lib/utils"
import type { RoutingDecision } from "@/lib/mock-data"

interface RoutingBadgeProps {
  routing: RoutingDecision
  size?: "sm" | "md" | "lg"
}

const routingLabels: Record<RoutingDecision, string> = {
  AUTO_APPROVE: "Auto Aprobado",
  HITL_STANDARD: "Revisión Estándar",
  HITL_PRIORITY: "Revisión Prioritaria",
  AUTO_REJECT: "Auto Rechazado",
}

export function RoutingBadge({ routing, size = "md" }: RoutingBadgeProps) {
  const colorClasses: Record<RoutingDecision, string> = {
    AUTO_APPROVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
    HITL_STANDARD: "bg-yellow-100 text-yellow-800 border-yellow-200",
    HITL_PRIORITY: "bg-orange-100 text-orange-800 border-orange-200",
    AUTO_REJECT: "bg-red-100 text-red-800 border-red-200",
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-2 text-lg font-bold",
  }

  return (
    <span className={cn(
      "inline-flex items-center rounded-lg border font-semibold",
      colorClasses[routing],
      sizeClasses[size]
    )}>
      {routingLabels[routing]}
    </span>
  )
}
