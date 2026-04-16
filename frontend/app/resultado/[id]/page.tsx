"use client"

import { use, useEffect, useState } from "react"
import Link from "next/link"
import { ArrowLeft, FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ExtractedDataTable } from "@/components/extracted-data-table"
import { ModelMetricsPanel } from "@/components/model-metrics-panel"
import { ValidationPanel } from "@/components/validation-panel"
import { RoutingDecisionPanel } from "@/components/routing-decision-panel"
import { RoutingBadge } from "@/components/routing-badge"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { formatDate, formatFileSize, type ProcessedDocument } from "@/lib/mock-data"
import { getDocument, adaptDocument, approveDocument } from "@/lib/api"

interface PageProps {
  params: Promise<{ id: string }>
}

export default function ResultadoPage({ params }: PageProps) {
  const { id } = use(params)
  const [document, setDocument] = useState<ProcessedDocument | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [approving, setApproving] = useState(false)
  const [approved, setApproved] = useState(false)

  useEffect(() => {
    getDocument(id)
      .then((raw) => {
        setDocument(adaptDocument(raw))
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [id])

  const handleApprove = async () => {
    if (!document) return
    setApproving(true)
    try {
      await approveDocument(document.document_id)
      setApproved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al enviar a SAP")
    } finally {
      setApproving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <div className="flex items-center gap-3 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Cargando resultado...</span>
        </div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 font-medium">{error || "Documento no encontrado"}</p>
          <Link href="/" className="mt-4 inline-block">
            <Button variant="outline">Volver al inicio</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="sticky top-16 z-20 border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <div className="h-6 w-px bg-slate-200" />
              <div>
                <h1 className="text-lg font-semibold text-slate-900">
                  Resultados del Documento
                </h1>
                <p className="text-sm text-slate-500">ID: {document.document_id}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-slate-500">Confidence global</p>
                <ConfidenceBadge confidence={document.confidence_score} size="md" />
              </div>
              <RoutingBadge routing={document.routing} size="md" />
            </div>
          </div>
        </div>
      </div>

      {/* Contenido */}
      <div className="mx-auto max-w-7xl p-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {approved && (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Documento enviado a SAP correctamente.
          </div>
        )}

        <div className="flex gap-6">
          {/* Columna izquierda - Preview sticky */}
          <div className="w-[35%] flex-shrink-0">
            <div className="sticky top-36 space-y-4">
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div className="relative aspect-[3/4] w-full bg-slate-100">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-slate-200">
                        <FileText className="h-8 w-8 text-slate-400" />
                      </div>
                      <p className="text-sm font-medium text-slate-600">{document.filename}</p>
                      <p className="text-xs text-slate-400">{formatFileSize(document.filesize)}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500">Proveedor</p>
                    <p className="font-medium text-slate-900">{document.provider}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Categoría</p>
                    <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800">
                      {document.category}
                    </span>
                  </div>
                  <div>
                    <p className="text-slate-500">Procesado</p>
                    <p className="font-medium text-slate-900">{formatDate(document.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Duración total</p>
                    <p className="font-medium text-slate-900">
                      {(document.stages.reduce((sum, s) => sum + s.duration_ms, 0) / 1000).toFixed(1)}s
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Columna derecha - Paneles */}
          <div className="flex-1 space-y-6">
            <ExtractedDataTable
              fields={document.extracted_fields}
              routing={document.routing}
            />
            <ModelMetricsPanel
              stages={document.stages}
              confidenceScore={document.confidence_score}
            />
            <ValidationPanel validation={document.validation} />
            <RoutingDecisionPanel
              routing={document.routing}
              reason={document.routing_reason}
              onApprove={handleApprove}
              approving={approving}
              approved={approved}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
