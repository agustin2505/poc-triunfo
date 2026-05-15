import { TT, ROUTING_META } from "@/lib/theme"
import type { RoutingDecision } from "@/lib/mock-data"
import { Check, Eye, AlertTriangle, X } from "lucide-react"

interface RoutingBadgeProps {
  routing: RoutingDecision
  size?: "sm" | "md" | "lg"
}

const icons: Record<string, React.ElementType> = {
  AUTO_APPROVE:  Check,
  HITL_STANDARD: Eye,
  HITL_PRIORITY: AlertTriangle,
  AUTO_REJECT:   X,
}

export function RoutingBadge({ routing, size = "md" }: RoutingBadgeProps) {
  const meta = ROUTING_META[routing] ?? ROUTING_META.AUTO_REJECT
  const colors = TT[meta.tone]
  const Icon = icons[routing] ?? X
  const iconSize = size === 'lg' ? 18 : 14
  const padding = size === 'lg' ? '8px 14px' : size === 'sm' ? '2px 8px' : '4px 10px'
  const fontSize = size === 'lg' ? 14 : size === 'sm' ? 11 : 12

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      background: colors.bg, color: colors.fg,
      fontSize, fontWeight: 600, padding, borderRadius: 8,
      whiteSpace: 'nowrap',
    }}>
      <Icon size={iconSize} style={{ flexShrink: 0 }} />
      {meta.label}
    </span>
  )
}
