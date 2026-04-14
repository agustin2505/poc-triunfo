import { cn } from "@/lib/utils"
import type { FieldSource } from "@/lib/mock-data"

interface SourceBadgeProps {
  source: FieldSource
}

const sourceLabels: Record<FieldSource, string> = {
  majority: "Mayoría",
  docai: "DocAI",
  tesseract: "Tesseract",
  vertex: "Vertex",
  missing: "Faltante",
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const colorClasses: Record<FieldSource, string> = {
    majority: "bg-indigo-100 text-indigo-700",
    docai: "bg-blue-100 text-blue-700",
    tesseract: "bg-purple-100 text-purple-700",
    vertex: "bg-teal-100 text-teal-700",
    missing: "bg-slate-100 text-slate-500",
  }

  return (
    <span className={cn(
      "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
      colorClasses[source]
    )}>
      {sourceLabels[source]}
    </span>
  )
}
