import { useEffect, useState } from 'react'
import { Sidebar } from '@/components/layout/sidebar'
import { Topbar } from '@/components/layout/topbar'
import { useBackendHealth } from '@/hooks/use-backend-health'

interface AppShellProps {
  title: string
  description?: string
  isLive?: boolean
  actions?: React.ReactNode
  children: React.ReactNode
}

export function AppShell({ title, description, isLive, actions, children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const backendIsLive = useBackendHealth()
  // Prefer the page's own resource state once it resolves; fall back to the
  // global /health ping so the badge is accurate even while that data loads.
  const effectiveIsLive = typeof isLive === 'boolean' ? isLive : backendIsLive

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [mobileOpen])

  return (
    <div className="flex min-h-svh bg-background">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          title={title}
          description={description}
          isLive={effectiveIsLive}
          actions={actions}
          onMenuClick={() => setMobileOpen(true)}
        />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
