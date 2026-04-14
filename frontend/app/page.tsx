"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { UploadZone } from "@/components/upload-zone"
import { PipelineStepper } from "@/components/pipeline-stepper"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { formatFileSize, type PipelineStage } from "@/lib/mock-data"

const providers = [
  { value: "auto", label: "Auto-detectar" },
  { value: "edenor", label: "Edenor" },
  { value: "metrogas", label: "Metrogas" },
  { value: "interna", label: "Factura Interna" },
]

const qualities = [
  { value: "buena", label: "Buena" },
  { value: "media", label: "Media" },
  { value: "mala", label: "Mala" },
]

const initialStages: PipelineStage[] = [
  { name: "INGESTED", duration_ms: 0, status: "PENDING" },
  { name: "CLASSIFIED", duration_ms: 0, status: "PENDING" },
  { name: "PROCESSING", duration_ms: 0, status: "PENDING" },
  { name: "EXTRACTED", duration_ms: 0, status: "PENDING" },
  { name: "VALIDATED", duration_ms: 0, status: "PENDING" },
  { name: "ROUTED", duration_ms: 0, status: "PENDING" },
]

export default function ProcessPage() {
  const router = useRouter()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<string | null>(null)
  const [providerHint, setProviderHint] = useState("auto")
  const [qualityHint, setQualityHint] = useState("buena")
  const [isProcessing, setIsProcessing] = useState(false)
  const [stages, setStages] = useState<PipelineStage[]>(initialStages)
  const [detectedProvider, setDetectedProvider] = useState<string | null>(null)
  const [detectedCategory, setDetectedCategory] = useState<string | null>(null)

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file)
    
    // Create preview URL for images
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file)
      setFilePreview(url)
    } else {
      // For PDFs, we'll show a placeholder
      setFilePreview(null)
    }
    
    // Reset processing state
    setStages(initialStages)
    setDetectedProvider(null)
    setDetectedCategory(null)
    setIsProcessing(false)
  }, [])

  const simulateProcessing = useCallback(async () => {
    if (!selectedFile) return

    setIsProcessing(true)
    const durations = [120, 800, 100, 1600, 250, 150]
    const stageNames = ["INGESTED", "CLASSIFIED", "PROCESSING", "EXTRACTED", "VALIDATED", "ROUTED"]

    for (let i = 0; i < stageNames.length; i++) {
      // Set current stage to processing
      setStages(prev => prev.map((s, idx) => 
        idx === i ? { ...s, status: "PROCESSING" } : s
      ))

      // Wait for the simulated duration
      await new Promise(resolve => setTimeout(resolve, durations[i]))

      // Set stage to success
      setStages(prev => prev.map((s, idx) => 
        idx === i ? { ...s, status: "SUCCESS", duration_ms: durations[i] } : s
      ))

      // After classification, show detected provider
      if (stageNames[i] === "CLASSIFIED") {
        setDetectedProvider("Edenor")
        setDetectedCategory("SERVICIOS")
      }
    }

    // Navigate to results after a short delay
    setTimeout(() => {
      router.push("/resultado/a1b2c3d4")
    }, 500)
  }, [selectedFile, router])

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => {
      if (filePreview) {
        URL.revokeObjectURL(filePreview)
      }
    }
  }, [filePreview])

  const handleReset = useCallback(() => {
    setSelectedFile(null)
    setFilePreview(null)
    setStages(initialStages)
    setDetectedProvider(null)
    setDetectedCategory(null)
    setIsProcessing(false)
  }, [])

  // Idle state - no file selected
  if (!selectedFile) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center p-8">
        <div className="w-full max-w-xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-semibold text-slate-900">Procesar Factura</h1>
            <p className="mt-2 text-slate-500">
              Subí una factura para iniciar el procesamiento OCR/IDP
            </p>
          </div>

          <UploadZone onFileSelect={handleFileSelect} />

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                Proveedor (sugerencia)
              </label>
              <Select value={providerHint} onValueChange={setProviderHint}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {providers.map(p => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                Calidad de imagen
              </label>
              <Select value={qualityHint} onValueChange={setQualityHint}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {qualities.map(q => (
                    <SelectItem key={q.value} value={q.value}>
                      {q.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button className="w-full bg-indigo-600 hover:bg-indigo-700" size="lg" disabled>
            Procesar
          </Button>
        </div>
      </div>
    )
  }

  // Processing state - file selected
  return (
    <div className="min-h-[calc(100vh-4rem)] p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-slate-900">Procesando Documento</h1>
          <Button variant="outline" onClick={handleReset} disabled={isProcessing}>
            Nueva factura
          </Button>
        </div>

        <div className="grid grid-cols-5 gap-8">
          {/* Left column - Image preview */}
          <div className="col-span-2 space-y-4">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              {filePreview ? (
                <div className="relative aspect-[3/4] w-full">
                  <Image
                    src={filePreview}
                    alt="Vista previa del documento"
                    fill
                    className="object-contain"
                  />
                </div>
              ) : (
                <div className="flex aspect-[3/4] items-center justify-center bg-slate-100">
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-slate-200">
                      <svg className="h-6 w-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <p className="text-sm text-slate-500">Documento PDF</p>
                  </div>
                </div>
              )}
            </div>
            <div className="rounded-lg bg-white p-4 border border-slate-200">
              <p className="font-medium text-slate-900 truncate">{selectedFile.name}</p>
              <p className="text-sm text-slate-500">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>

          {/* Right column - Pipeline stepper */}
          <div className="col-span-3">
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="mb-6 text-lg font-semibold text-slate-900">
                Estado del Pipeline
              </h2>
              
              <PipelineStepper 
                stages={stages} 
                provider={detectedProvider ?? undefined}
                category={detectedCategory ?? undefined}
              />

              {!isProcessing && (
                <div className="mt-8">
                  <Button 
                    className="w-full bg-indigo-600 hover:bg-indigo-700" 
                    size="lg"
                    onClick={simulateProcessing}
                  >
                    Iniciar Procesamiento
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
