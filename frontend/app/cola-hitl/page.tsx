"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Clock, AlertTriangle, FileText, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { RoutingBadge } from "@/components/routing-badge"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { formatDate, type ProcessedDocument } from "@/lib/mock-data"
import { listDocuments, adaptListItem } from "@/lib/api"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export default function ColaHITLPage() {
  const [documents, setDocuments] = useState<ProcessedDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDocuments(100)
      .then((data) => {
        const hitl = data.documents
          .map(adaptListItem)
          .filter(
            (d) => d.routing === "HITL_STANDARD" || d.routing === "HITL_PRIORITY"
          )
        setDocuments(hitl)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const priorityCount = documents.filter((d) => d.routing === "HITL_PRIORITY").length
  const standardCount = documents.filter((d) => d.routing === "HITL_STANDARD").length

  return (
    <div className="min-h-[calc(100vh-4rem)] p-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-900">Cola de Revisión Manual</h1>
          <p className="text-slate-500">Documentos pendientes de revisión humana</p>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100">
                <FileText className="h-6 w-6 text-slate-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total en cola</p>
                <p className="text-2xl font-bold text-slate-900">{documents.length}</p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-orange-200 bg-orange-50 p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-orange-100">
                <AlertTriangle className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-orange-700">Prioritarios</p>
                <p className="text-2xl font-bold text-orange-900">{priorityCount}</p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-yellow-100">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-yellow-700">Estándar</p>
                <p className="text-2xl font-bold text-yellow-900">{standardCount}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabla */}
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
            <h3 className="font-semibold text-slate-900">Documentos Pendientes</h3>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16 gap-3 text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Cargando cola...</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-16">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 mb-4">
                <FileText className="h-8 w-8 text-emerald-600" />
              </div>
              <p className="text-lg font-medium text-slate-900">Cola vacía</p>
              <p className="text-sm text-slate-500">No hay documentos pendientes de revisión</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Archivo</TableHead>
                  <TableHead>Proveedor</TableHead>
                  <TableHead className="text-center">Confidence</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Acción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow
                    key={doc.document_id}
                    className={cn(
                      doc.routing === "HITL_PRIORITY" && "bg-orange-50/50"
                    )}
                  >
                    <TableCell className="font-mono text-sm">
                      {doc.document_id.slice(0, 8)}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">{doc.filename}</TableCell>
                    <TableCell>{doc.provider}</TableCell>
                    <TableCell className="text-center">
                      <ConfidenceBadge confidence={doc.confidence_score} size="sm" />
                    </TableCell>
                    <TableCell className="text-center">
                      <RoutingBadge routing={doc.routing} size="sm" />
                    </TableCell>
                    <TableCell className="text-slate-500">
                      {formatDate(doc.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/resultado/${doc.document_id}`}>
                        <Button size="sm" variant="outline">
                          Revisar
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  )
}
