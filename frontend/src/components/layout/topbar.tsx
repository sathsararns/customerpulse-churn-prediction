import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { DEMO_MODE } from '@/services/api'
import { cn } from '@/lib/utils'

interface TopbarProps {
  title: string
  description?: string
  onMenuClick: () => void
  isLive?: boolean
  serviceStatus: string
  actions?: React.ReactNode
}

export function Topbar({ title, description, onMenuClick, isLive, serviceStatus, actions }: TopbarProps) {
  const dataLabel = DEMO_MODE ? 'Demo mode' : isLive === undefined ? 'Checking' : isLive ? 'Live data' : 'Unavailable'
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-lg sm:px-6">
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick} aria-label="Open navigation"><Menu className="h-5 w-5" /></Button>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg">{title}</h1>
          <span className={cn('hidden rounded-full border px-2 py-0.5 text-[11px] sm:inline-flex',
            isLive && !DEMO_MODE ? 'border-success/30 text-success' : 'border-warning/30 text-warning')}>{dataLabel}</span>
          <span className="hidden text-[11px] text-muted-foreground md:inline">{DEMO_MODE ? 'Illustration' : `API: ${serviceStatus === 'ok' ? 'ready' : serviceStatus}`}</span>
        </div>
        {description && <p className="hidden truncate text-xs text-muted-foreground sm:block">{description}</p>}
      </div>
      <div className="flex items-center gap-2">{actions}<ThemeToggle /></div>
    </header>
  )
}
