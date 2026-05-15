"use client"

import { usePathname } from "next/navigation"
import { Bell } from "lucide-react"
import { TT } from "@/lib/theme"

const PAGE_TITLES: Record<string, string> = {
  "/": "Subir documento",
  "/cola-hitl": "Cola HITL",
  "/metricas": "Métricas del pipeline",
}

function getTitle(pathname: string): string {
  if (pathname.startsWith("/resultado/")) return "Resultado del documento"
  return PAGE_TITLES[pathname] ?? "Triunfo MVP"
}

export function TopBar() {
  const pathname = usePathname()
  const title = getTitle(pathname)

  return (
    <header style={{
      height: 56, background: TT.surface, borderBottom: `1px solid ${TT.border}`,
      display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16,
      position: 'sticky', top: 0, zIndex: 30,
    }}>
      <nav style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: TT.muted, flex: 1 }}>
        <span style={{ color: TT.subtle }}>Triunfo MVP</span>
        <span style={{ color: TT.subtle }}>/</span>
        <span style={{ color: TT.fg, fontWeight: 500 }}>{title}</span>
      </nav>
      <button style={{
        background: 'transparent', border: 'none', color: TT.muted,
        cursor: 'pointer', padding: 8, borderRadius: 8, display: 'inline-flex',
      }}>
        <Bell size={18} />
      </button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 30, height: 30, borderRadius: 999, background: TT.accent, color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 600, fontSize: 12,
        }}>OP</div>
        <div style={{ lineHeight: 1.2 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: TT.fg }}>Operador</div>
          <div style={{ fontSize: 11, color: TT.muted }}>Back-office</div>
        </div>
      </div>
    </header>
  )
}
