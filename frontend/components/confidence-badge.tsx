import { cn } from "@/lib/utils"
import { formatConfidence, getConfidenceColor } from "@/lib/mock-data"

interface ConfidenceBadgeProps {
  confidence: number
  size?: "sm" | "md" | "lg"
  showLabel?: boolean
}

export function ConfidenceBadge({ confidence, size = "md", showLabel = true }: ConfidenceBadgeProps) {
  const color = getConfidenceColor(confidence)
  
  const colorClasses = {
    green: "bg-emerald-100 text-emerald-800",
    yellow: "bg-yellow-100 text-yellow-800",
    red: "bg-red-100 text-red-800",
  }

  const sizeClasses = {
    sm: "px-1.5 py-0.5 text-xs",
    md: "px-2 py-0.5 text-sm",
    lg: "px-3 py-1 text-base font-semibold",
  }

  if (confidence === 0) {
    return <span className="text-slate-400">—</span>
  }

  return (
    <span className={cn(
      "inline-flex items-center rounded-md font-medium",
      colorClasses[color],
      sizeClasses[size]
    )}>
      {showLabel ? formatConfidence(confidence) : formatConfidence(confidence)}
    </span>
  )
}
