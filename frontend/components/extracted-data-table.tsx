"use client"

import { useState } from "react"
import { Pencil } from "lucide-react"
import { cn } from "@/lib/utils"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { SourceBadge } from "@/components/source-badge"
import { 
  type ExtractedField, 
  type RoutingDecision,
  fieldLabels, 
  criticalFields,
  formatCurrency,
  formatDate 
} from "@/lib/mock-data"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface ExtractedDataTableProps {
  fields: Record<string, ExtractedField>
  routing: RoutingDecision
  onFieldClick?: (fieldName: string, field: ExtractedField) => void
}

const amountFields = ["net_amount", "vat_amount", "total_amount"]
const dateFields = ["invoice_date", "due_date", "cae_due_date"]

function formatFieldValue(fieldName: string, value: string | number | null): string {
  if (value === null) return "—"
  if (amountFields.includes(fieldName)) {
    return formatCurrency(value as number)
  }
  if (dateFields.includes(fieldName)) {
    return formatDate(value as string)
  }
  return String(value)
}

export function ExtractedDataTable({ fields, routing, onFieldClick }: ExtractedDataTableProps) {
  const [selectedField, setSelectedField] = useState<{ name: string; field: ExtractedField } | null>(null)
  const isEditable = routing === "HITL_STANDARD" || routing === "HITL_PRIORITY"
  
  const fieldOrder = [
    "supplier_name", "supplier_cuit", "invoice_type", "invoice_number",
    "invoice_date", "due_date", "currency", "net_amount", "vat_amount",
    "total_amount", "cae", "cae_due_date"
  ]

  const handleRowClick = (fieldName: string, field: ExtractedField) => {
    setSelectedField({ name: fieldName, field })
    onFieldClick?.(fieldName, field)
  }

  return (
    <>
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
          <h3 className="font-semibold text-slate-900">Datos Extraídos</h3>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">Campo</TableHead>
                <TableHead className="w-[160px]">Valor Final</TableHead>
                <TableHead className="w-[80px] text-center">Conf.</TableHead>
                <TableHead className="w-[90px] text-center">Fuente</TableHead>
                <TableHead className="w-[80px] text-center">DocAI</TableHead>
                <TableHead className="w-[80px] text-center">Tesseract</TableHead>
                <TableHead className="w-[80px] text-center">Vertex</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {fieldOrder.map((fieldName) => {
                const field = fields[fieldName]
                if (!field) return null
                
                const isCritical = criticalFields.includes(fieldName)
                
                return (
                  <TableRow 
                    key={fieldName}
                    onClick={() => handleRowClick(fieldName, field)}
                    className={cn(
                      "cursor-pointer hover:bg-slate-50",
                      isCritical && "bg-indigo-50/50"
                    )}
                  >
                    <TableCell className="font-medium">
                      <span className={cn(isCritical && "text-indigo-700")}>
                        {fieldLabels[fieldName] || fieldName}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          field.value === null && "text-slate-400"
                        )}>
                          {formatFieldValue(fieldName, field.value)}
                        </span>
                        {isEditable && field.value !== null && (
                          <Pencil className="h-3.5 w-3.5 text-slate-400" />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <ConfidenceBadge confidence={field.confidence} size="sm" />
                    </TableCell>
                    <TableCell className="text-center">
                      <SourceBadge source={field.source} />
                    </TableCell>
                    <TableCell className="text-center">
                      {field.agentA ? (
                        <ConfidenceBadge confidence={field.agentA.confidence} size="sm" />
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {field.agentB ? (
                        <ConfidenceBadge confidence={field.agentB.confidence} size="sm" />
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {field.agentC && field.agentC.confidence > 0 ? (
                        <ConfidenceBadge confidence={field.agentC.confidence} size="sm" />
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Agent Detail Modal */}
      <Dialog open={selectedField !== null} onOpenChange={() => setSelectedField(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Detalle: {selectedField ? fieldLabels[selectedField.name] : ""}
            </DialogTitle>
          </DialogHeader>
          
          {selectedField && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Valor Final</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {formatFieldValue(selectedField.name, selectedField.field.value)}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Confianza</p>
                  <ConfidenceBadge confidence={selectedField.field.confidence} size="lg" />
                </div>
              </div>

              <div className="rounded-lg border border-slate-200">
                <div className="border-b border-slate-200 bg-slate-50 px-4 py-2">
                  <h4 className="text-sm font-medium text-slate-700">Valores por Agente</h4>
                </div>
                <div className="divide-y divide-slate-100">
                  {selectedField.field.agentA && (
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">DocAI</span>
                        <span>{formatFieldValue(selectedField.name, selectedField.field.agentA.value)}</span>
                      </div>
                      <ConfidenceBadge confidence={selectedField.field.agentA.confidence} size="sm" />
                    </div>
                  )}
                  {selectedField.field.agentB && (
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">Tesseract</span>
                        <span>{formatFieldValue(selectedField.name, selectedField.field.agentB.value)}</span>
                      </div>
                      <ConfidenceBadge confidence={selectedField.field.agentB.confidence} size="sm" />
                    </div>
                  )}
                  {selectedField.field.agentC && (
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-700">Vertex</span>
                        <span>
                          {selectedField.field.agentC.confidence > 0 
                            ? formatFieldValue(selectedField.name, selectedField.field.agentC.value)
                            : "Saltado"
                          }
                        </span>
                      </div>
                      {selectedField.field.agentC.confidence > 0 ? (
                        <ConfidenceBadge confidence={selectedField.field.agentC.confidence} size="sm" />
                      ) : (
                        <span className="text-xs text-slate-400">N/A</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="text-center">
                <SourceBadge source={selectedField.field.source} />
                <p className="mt-2 text-xs text-slate-500">
                  Fuente seleccionada para el valor final
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
