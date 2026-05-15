"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Upload, Inbox, BarChart3 } from "lucide-react"
import { TT } from "@/lib/theme"

const navItems = [
  { href: "/",         label: "Subir",     Icon: Upload },
  { href: "/cola-hitl", label: "Cola HITL", Icon: Inbox },
  { href: "/metricas",  label: "Métricas",  Icon: BarChart3 },
]

interface SidebarProps {
  queueCount?: number
}

export function Sidebar({ queueCount = 0 }: SidebarProps) {
  const pathname = usePathname()

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href)

  return (
    <aside style={{
      width: 232, background: TT.primary, color: '#fff',
      display: 'flex', flexDirection: 'column',
      position: 'fixed', top: 0, left: 0, height: '100vh', zIndex: 40,
    }}>
      <div style={{
        padding: '20px 20px 14px', display: 'flex', alignItems: 'center', gap: 10,
        borderBottom: '1px solid rgba(255,255,255,.1)',
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 8,
          background: 'rgba(255,255,255,.12)', border: '1px solid rgba(255,255,255,.18)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: 14, fontFamily: 'monospace',
        }}>TS</div>
        <div style={{ lineHeight: 1.15 }}>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '.04em' }}>TRIUNFO MVP</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,.7)' }}>OCR / IDP · v0.4</div>
        </div>
      </div>

      <nav style={{ padding: 12, flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {navItems.map(({ href, label, Icon }) => {
          const active = isActive(href)
          return (
            <Link key={href} href={href} style={{
              position: 'relative', display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 14px', fontSize: 14, fontWeight: 500,
              background: active ? 'rgba(255,255,255,.08)' : 'transparent',
              color: active ? '#fff' : 'rgba(255,255,255,.85)',
              borderRadius: 8, textDecoration: 'none', transition: 'background 150ms ease',
            }}>
              {active && (
                <span style={{
                  position: 'absolute', left: -12, top: 8, bottom: 8,
                  width: 3, background: TT.accent, borderRadius: '0 3px 3px 0',
                }} />
              )}
              <Icon size={18} style={{ color: active ? '#fff' : 'rgba(255,255,255,.75)', flexShrink: 0 }} />
              <span style={{ flex: 1 }}>{label}</span>
              {href === "/cola-hitl" && queueCount > 0 && (
                <span style={{
                  background: TT.accent, color: '#fff',
                  fontSize: 11, fontWeight: 600, padding: '1px 7px', borderRadius: 999,
                }}>{queueCount}</span>
              )}
            </Link>
          )
        })}
      </nav>

      <div style={{
        padding: 16, borderTop: '1px solid rgba(255,255,255,.1)',
        fontSize: 12, color: 'rgba(255,255,255,.65)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 6, height: 6, borderRadius: 999, background: TT.approve.solid }} />
          Pipeline operativo
        </div>
        <div style={{ marginTop: 4, fontFamily: 'monospace' }}>build 2026.05.12-rc1</div>
      </div>
    </aside>
  )
}
