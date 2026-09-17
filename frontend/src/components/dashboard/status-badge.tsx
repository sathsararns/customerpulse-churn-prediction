import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: 'healthy' | 'degraded' | 'down' | 'trained' | 'training' | 'idle' | 'failed'
  className?: string
}

const STATUS_MAP: Record<StatusBadgeProps['status'], { variant: 'success' | 'warning' | 'destructive' | 'secondary'; label: string; pulse?: boolean }> = {
  healthy: { variant: 'success', label: 'Healthy', pulse: true },
  trained: { variant: 'success', label: 'Trained' },
  degraded: { variant: 'warning', label: 'Degraded' },
  training: { variant: 'warning', label: 'Training', pulse: true },
  idle: { variant: 'secondary', label: 'Idle' },
  down: { variant: 'destructive', label: 'Down' },
  failed: { variant: 'destructive', label: 'Failed' },
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_MAP[status]

  return (
    <Badge variant={config.variant} className={cn('font-semibold', className)}>
      <span className="relative flex h-1.5 w-1.5">
        {config.pulse && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
        )}
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      {config.label}
    </Badge>
  )
}
