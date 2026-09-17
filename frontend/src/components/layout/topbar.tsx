import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { cn } from '@/lib/utils'

interface TopbarProps {
  title: string
  description?: string
  onMenuClick: () => void
  isLive?: boolean
  actions?: React.ReactNode
}

export function Topbar({ title, description, onMenuClick, isLive, actions }: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-lg sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg">{title}</h1>
          {typeof isLive === 'boolean' && (
            <span
              className={cn(
                'hidden items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium sm:inline-flex',
                isLive
                  ? 'border-success/30 bg-success/10 text-success'
                  : 'border-warning/30 bg-warning/10 text-warning',
              )}
            >
              <span className={cn('h-1.5 w-1.5 rounded-full', isLive ? 'bg-success' : 'bg-warning')} />
              {isLive ? 'Live data' : 'Demo data'}
            </span>
          )}
        </div>
        {description && (
          <p className="hidden truncate text-xs text-muted-foreground sm:block">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        {actions}
        <ThemeToggle />
      </div>
    </header>
  )
}
