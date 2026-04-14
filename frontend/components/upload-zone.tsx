"use client"

import { useCallback, useState } from "react"
import { Upload, FileImage } from "lucide-react"
import { cn } from "@/lib/utils"

interface UploadZoneProps {
  onFileSelect: (file: File) => void
  disabled?: boolean
}

export function UploadZone({ onFileSelect, disabled }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) setIsDragOver(true)
  }, [disabled])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (disabled) return

    const file = e.dataTransfer.files[0]
    if (file && isValidFileType(file)) {
      onFileSelect(file)
    }
  }, [disabled, onFileSelect])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && isValidFileType(file)) {
      onFileSelect(file)
    }
  }, [onFileSelect])

  const isValidFileType = (file: File) => {
    const validTypes = ["image/jpeg", "image/png", "application/pdf"]
    return validTypes.includes(file.type)
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors",
        isDragOver
          ? "border-indigo-500 bg-indigo-50"
          : "border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <input
        type="file"
        accept=".jpg,.jpeg,.png,.pdf"
        onChange={handleFileInput}
        className="absolute inset-0 z-10 cursor-pointer opacity-0"
        disabled={disabled}
      />
      
      <div className={cn(
        "mb-4 flex h-16 w-16 items-center justify-center rounded-full",
        isDragOver ? "bg-indigo-100" : "bg-slate-100"
      )}>
        {isDragOver ? (
          <FileImage className="h-8 w-8 text-indigo-600" />
        ) : (
          <Upload className="h-8 w-8 text-slate-400" />
        )}
      </div>
      
      <p className="mb-2 text-lg font-medium text-slate-700">
        Arrastrá tu factura aquí
      </p>
      <p className="text-sm text-slate-500">
        JPEG, PNG, PDF
      </p>
    </div>
  )
}
