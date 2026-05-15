"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Send } from "lucide-react"
import { UploadZone } from "@/components/upload-zone"
import { PipelineStepper } from "@/components/pipeline-stepper"
import { TT } from "@/lib/theme"
import { uploadDocument } from "@/lib/api"
import type { PipelineStage } from "@/lib/mock-data"

const PROVIDERS = ['Edenor', 'Metrogas', 'Factura Interna']
const QUALITIES = [
  { value: 'good',   label: 'Buena · escaneo nítido' },
  { value: 'medium', label: 'Media · foto de celular' },
  { value: 'poor',   label: 'Baja · borroso o rotado' },
]

const PROVIDER_MAP: Record<string, string> = {
  'Edenor': 'edenor-001',
  'Metrogas': 'metrogas-001',
  'Factura Interna': 'factura-interna-001',
}

const INITIAL_STAGES: PipelineStage[] = [
  { name: "INGESTED",   duration_ms: 0, status: "PENDING" },
  { name: "CLASSIFIED", duration_ms: 0, status: "PENDING" },
  { name: "PROCESSING", duration_ms: 0, status: "PENDING" },
  { name: "EXTRACTED",  duration_ms: 0, status: "PENDING" },
  { name: "VALIDATED",  duration_ms: 0, status: "PENDING" },
  { name: "ROUTED",     duration_ms: 0, status: "PENDING" },
]

const STAGE_DURATIONS = [150, 600, 120, 1200, 300, 200]

function SelectField({ label, hint, value, onChange, options }: {
  label: string
  hint?: string
  value: string
  onChange: (v: string) => void
  options: (string | { value: string; label: string })[]
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ fontSize: 13, fontWeight: 500, color: TT.fg }}>{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          height: 38, padding: '0 32px 0 12px', fontSize: 14, fontFamily: 'inherit',
          background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 8,
          color: TT.fg, appearance: 'none', cursor: 'pointer',
          backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2'><polyline points='6 9 12 15 18 9'/></svg>")`,
          backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center',
        }}
      >
        {options.map(o => {
          const val = typeof o === 'string' ? o : o.value
          const lbl = typeof o === 'string' ? o : o.label
          return <option key={val} value={val}>{lbl}</option>
        })}
      </select>
      {hint && <div style={{ fontSize: 12, color: TT.muted }}>{hint}</div>}
    </div>
  )
}

export default function ProcessPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [provider, setProvider] = useState('Edenor')
  const [quality, setQuality] = useState('medium')
  const [processing, setProcessing] = useState(false)
  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_STAGES)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const handleProcess = useCallback(async () => {
    if (!file) return
    setProcessing(true)
    setCurrentIdx(0)
    setError(null)

    const fetchPromise = uploadDocument(file, {
      providerHint: PROVIDER_MAP[provider] ?? provider,
      qualityHint: quality,
    })

    for (let i = 0; i < INITIAL_STAGES.length; i++) {
      setCurrentIdx(i)
      await new Promise(resolve => setTimeout(resolve, Math.max(120, STAGE_DURATIONS[i] * 0.4)))
    }

    try {
      const result = await fetchPromise
      if (result.processing_summary?.stages) {
        setStages(result.processing_summary.stages.map(s => ({
          name: s.name,
          duration_ms: s.duration_ms,
          status: s.status as PipelineStage["status"],
        })))
      }
      setCurrentIdx(INITIAL_STAGES.length)
      setTimeout(() => router.push(`/resultado/${result.document_id}`), 400)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al procesar el documento")
      setProcessing(false)
      setStages(INITIAL_STAGES)
      setCurrentIdx(0)
    }
  }, [file, provider, quality, router])

  const handleClear = useCallback(() => {
    setFile(null)
    setProcessing(false)
    setStages(INITIAL_STAGES)
    setCurrentIdx(0)
    setError(null)
  }, [])

  return (
    <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 32px 64px' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-.01em', margin: 0, lineHeight: 1.28, color: TT.fg }}>
          Procesar documento
        </h1>
        <p style={{ fontSize: 15, color: TT.muted, marginTop: 6, lineHeight: 1.55 }}>
          Subí una factura para que el pipeline OCR/IDP extraiga sus datos y proponga una decisión de routing.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <UploadZone file={file} onFile={setFile} onClear={handleClear} />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <SelectField
            label="Proveedor"
            value={provider}
            onChange={setProvider}
            options={PROVIDERS}
            hint="Determina las validaciones específicas que se aplicarán."
          />
          <SelectField
            label="Calidad del documento"
            value={quality}
            onChange={setQuality}
            options={QUALITIES}
            hint="Ajusta el umbral de confidence y activa fallback si es baja."
          />
        </div>

        {processing && (
          <div style={{ background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: TT.muted, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 16 }}>
              Procesando · {Math.min(currentIdx + 1, INITIAL_STAGES.length)}/{INITIAL_STAGES.length}
            </div>
            <PipelineStepper stages={stages} currentIdx={currentIdx} animated />
          </div>
        )}

        {error && (
          <div style={{ background: '#FEF2F2', border: `1px solid #FECACA`, borderRadius: 8, padding: '12px 16px', fontSize: 14, color: '#B91C1C' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 8 }}>
          <div style={{ fontSize: 13, color: TT.muted }}>El procesamiento tarda entre 2 y 4 segundos.</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleClear}
              disabled={!file || processing}
              style={{
                height: 38, padding: '0 14px', fontSize: 14, fontWeight: 500, borderRadius: 8,
                background: 'transparent', color: TT.fg, border: 'none', cursor: !file || processing ? 'not-allowed' : 'pointer',
                opacity: !file || processing ? 0.5 : 1,
              }}
            >
              Limpiar
            </button>
            <button
              onClick={handleProcess}
              disabled={!file || processing}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                height: 38, padding: '0 14px', fontSize: 14, fontWeight: 500, borderRadius: 8,
                background: !file || processing ? TT.accentSoft : TT.accent, color: !file || processing ? TT.accentHover : '#fff',
                border: 'none', cursor: !file || processing ? 'not-allowed' : 'pointer', transition: 'all 150ms ease',
              }}
            >
              <Send size={15} /> Procesar documento
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
