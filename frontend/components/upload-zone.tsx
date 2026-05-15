"use client"

import { useCallback, useState, useRef } from "react"
import { Upload, FileText, Image as ImageIcon, X } from "lucide-react"
import { TT } from "@/lib/theme"

interface UploadZoneProps {
  file?: File | null
  onFile: (file: File) => void
  onClear?: () => void
}

function fileSizeStr(size: number): string {
  if (size > 1e6) return (size / 1e6).toFixed(2) + ' MB'
  return (size / 1024).toFixed(0) + ' KB'
}

export function UploadZone({ file, onFile, onClear }: UploadZoneProps) {
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files?.[0]
    if (f) onFile(f)
  }, [onFile])

  if (file) {
    const isPdf = file.type === 'application/pdf' || file.name.endsWith('.pdf')
    return (
      <div style={{
        background: TT.surface, border: `1px solid ${TT.border}`, borderRadius: 12,
        padding: 20, display: 'flex', alignItems: 'center', gap: 16,
        boxShadow: '0 1px 2px rgba(16,24,40,.05)',
      }}>
        <div style={{
          width: 56, height: 72, borderRadius: 8, background: TT.accentSoft, color: TT.accent,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, position: 'relative',
        }}>
          {isPdf ? <FileText size={22} /> : <ImageIcon size={22} />}
          <span style={{
            position: 'absolute', bottom: 6, fontSize: 9, fontWeight: 700,
            letterSpacing: '.04em', textTransform: 'uppercase', fontFamily: 'monospace',
          }}>{isPdf ? 'PDF' : 'IMG'}</span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 500, color: TT.fg, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {file.name}
          </div>
          <div style={{ fontSize: 13, color: TT.muted, marginTop: 2 }}>
            {fileSizeStr(file.size)} · {file.type || 'aplicación binaria'}
          </div>
        </div>
        {onClear && (
          <button onClick={onClear} style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'transparent', border: `1px solid ${TT.border}`, borderRadius: 8,
            padding: '6px 12px', fontSize: 13, color: TT.muted, cursor: 'pointer',
          }}>
            <X size={14} /> Quitar
          </button>
        )}
      </div>
    )
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      style={{
        background: drag ? TT.accentSoft : TT.surface,
        border: `2px dashed ${drag ? TT.accent : TT.border}`,
        borderRadius: 12, padding: 48,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 12, cursor: 'pointer', transition: 'all 150ms ease',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,application/pdf"
        style={{ display: 'none' }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
      <div style={{
        width: 56, height: 56, borderRadius: 999,
        background: drag ? TT.surface : TT.accentSoft, color: TT.accent,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Upload size={24} />
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: TT.fg }}>
        Arrastrá la factura o hacé click para seleccionar
      </div>
      <div style={{ fontSize: 13, color: TT.muted }}>PDF, JPEG o PNG · hasta 10 MB</div>
    </div>
  )
}
