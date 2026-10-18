import { useEffect, useState } from 'react'
import { Sidebar } from '@/components/layout/sidebar'
import { Topbar } from '@/components/layout/topbar'
import { useBackendHealth } from '@/hooks/use-backend-health'
import { DEMO_MODE } from '@/services/api'

interface AppShellProps {
  title: string
  description?: string
  isLive?: boolean
  actions?: React.ReactNode
  children: React.ReactNode
}

export function AppShell({ title, description, isLive, actions, children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const health = useBackendHealth()
  const status = health.loading ? 'checking' : health.error ? 'offline' : health.data?.status ?? 'offline'
  const effectiveIsLive = typeof isLive === 'boolean' ? isLive : health.loading ? undefined : health.isLive

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [mobileOpen])

  return (
    <div className="flex min-h-svh bg-background">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)}
        serviceStatus={status} modelVersion={health.data?.model_version} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} description={description} isLive={effectiveIsLive}
          serviceStatus={status} actions={actions} onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto w-full max-w-7xl">
            {DEMO_MODE && <p role="status" className="mb-5 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">Demo mode: sample data and heuristic predictions. No backend calls are made.</p>}
            {!DEMO_MODE && health.error && <p role="alert" className="mb-5 rounded-lg border border-destructive/30 p-3 text-sm">{health.error}</p>}
            {!DEMO_MODE && health.data?.status === 'degraded' && <p role="status" className="mb-5 rounded-lg border border-warning/40 p-3 text-sm">The API is reachable, but model serving or prediction storage needs attention.</p>}
            {!DEMO_MODE && health.data?.reload_required && <p role="status" className="mb-5 rounded-lg border border-warning/40 p-3 text-sm">A different model version has been selected. Restart the API to load it. Results below identify the model currently serving.</p>}
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
