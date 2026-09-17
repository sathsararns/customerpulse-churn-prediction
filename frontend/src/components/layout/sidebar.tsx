import { Link, NavLink } from 'react-router-dom'
import {
  Activity,
  BarChart3,
  Cpu,
  Gauge,
  Radio,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'

const NAV_ITEMS = [
  { to: '/app/predict', label: 'Predict Churn', icon: Gauge },
  { to: '/app/metrics', label: 'Model Metrics', icon: BarChart3 },
  { to: '/app/activity', label: 'Recent Activity', icon: Activity },
  { to: '/app/model', label: 'Model Info', icon: Cpu },
]

interface SidebarProps {
  mobileOpen: boolean
  onClose: () => void
}

export function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-300 ease-out lg:sticky lg:top-0 lg:h-svh lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-brand shadow-glow">
              <Radio className="h-4 w-4 text-white" />
            </span>
            <span className="text-sm font-bold tracking-tight text-sidebar-foreground">
              CustomerPulse <span className="text-gradient-brand">AI</span>
            </span>
          </Link>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <Separator className="bg-sidebar-border" />

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Workspace
          </p>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
                  isActive &&
                    'bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary',
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <Separator className="bg-sidebar-border" />

        <div className="p-4">
          <div className="rounded-xl border border-sidebar-border bg-gradient-to-br from-primary/10 via-transparent to-transparent p-4">
            <p className="text-xs font-semibold text-foreground">Model status</p>
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              Pipeline healthy
            </p>
          </div>
        </div>
      </aside>
    </>
  )
}
