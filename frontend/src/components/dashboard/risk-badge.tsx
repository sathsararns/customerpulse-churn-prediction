import { AlertTriangle, ShieldCheck, ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { RiskLevel } from '@/types'
import { cn } from '@/lib/utils'

const RISK_CONFIG: Record<RiskLevel, { variant: 'success' | 'warning' | 'destructive'; icon: typeof ShieldCheck }> = {
  Low: { variant: 'success', icon: ShieldCheck },
  Medium: { variant: 'warning', icon: ShieldAlert },
  High: { variant: 'destructive', icon: AlertTriangle },
}

export function RiskBadge({ level, className }: { level: RiskLevel; className?: string }) {
  const config = RISK_CONFIG[level]
  const Icon = config.icon

  return (
    <Badge variant={config.variant} className={cn('font-semibold', className)}>
      <Icon className="h-3 w-3" />
      {level} risk
    </Badge>
  )
}
