"use client"

import { ChevronDown, User } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"

const sedes = [
  { id: "demo-001", name: "demo-001" },
  { id: "prod-001", name: "prod-001" },
  { id: "test-001", name: "test-001" },
]

interface TopBarProps {
  selectedSede?: string
  userName?: string
}

export function TopBar({ selectedSede = "demo-001", userName = "Operador" }: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      {/* Sede Selector */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="gap-2">
            <span className="text-slate-500">Sede:</span>
            <span className="font-medium">{selectedSede}</span>
            <ChevronDown className="h-4 w-4 text-slate-400" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {sedes.map((sede) => (
            <DropdownMenuItem key={sede.id}>
              {sede.name}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* User Info */}
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="text-sm font-medium text-slate-900">{userName}</p>
          <p className="text-xs text-slate-500">Back-office</p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100">
          <User className="h-5 w-5 text-slate-600" />
        </div>
      </div>
    </header>
  )
}
