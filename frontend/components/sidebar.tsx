"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { FileUp, ListTodo, BarChart3 } from "lucide-react"

const navItems = [
  { href: "/", label: "Procesar", icon: FileUp },
  { href: "/cola-hitl", label: "Cola HITL", icon: ListTodo },
  { href: "/metricas", label: "Métricas", icon: BarChart3 },
]

type HealthStatus = "healthy" | "degraded" | "down"

interface SidebarProps {
  healthStatus?: HealthStatus
}

export function Sidebar({ healthStatus = "healthy" }: SidebarProps) {
  const pathname = usePathname()

  const getHealthColor = (status: HealthStatus) => {
    switch (status) {
      case "healthy": return "bg-emerald-500"
      case "degraded": return "bg-yellow-500"
      case "down": return "bg-red-500"
    }
  }

  const getHealthLabel = (status: HealthStatus) => {
    switch (status) {
      case "healthy": return "Sistema operativo"
      case "degraded": return "Rendimiento degradado"
      case "down": return "Sistema caído"
    }
  }

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col bg-slate-900 text-white">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-slate-700 px-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-bold">
            T
          </div>
          <span className="text-xl font-semibold tracking-tight">Triunfo</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== "/" && pathname.startsWith(item.href)) ||
            (item.href === "/" && pathname === "/")
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Health Indicator */}
      <div className="border-t border-slate-700 px-4 py-4">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <div className={cn("h-2.5 w-2.5 rounded-full", getHealthColor(healthStatus))} />
          <span>{getHealthLabel(healthStatus)}</span>
        </div>
      </div>
    </aside>
  )
}
