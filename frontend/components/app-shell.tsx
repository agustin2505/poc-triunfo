"use client"

import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar healthStatus="healthy" />
      <div className="pl-60">
        <TopBar selectedSede="demo-001" userName="María García" />
        <main className="min-h-[calc(100vh-4rem)]">
          {children}
        </main>
      </div>
    </div>
  )
}
