"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { listDocuments } from "@/lib/api"
import { TT } from "@/lib/theme"

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [queueCount, setQueueCount] = useState(0)

  useEffect(() => {
    listDocuments(200)
      .then((data) => {
        const count = data.documents.filter(
          (d) => d.routing === "HITL_STANDARD" || d.routing === "HITL_PRIORITY"
        ).length
        setQueueCount(count)
      })
      .catch(() => {})
  }, [])

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: TT.background }}>
      <Sidebar queueCount={queueCount} />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', marginLeft: 232 }}>
        <TopBar />
        <main style={{ flex: 1 }}>
          {children}
        </main>
      </div>
    </div>
  )
}
