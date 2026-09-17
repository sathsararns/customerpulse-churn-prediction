import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { ArrowDownRight, ArrowUpRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface KpiCardProps {
  label: string
  value: string
  icon: LucideIcon
  delta?: { value: string; direction: 'up' | 'down'; positive?: boolean }
  accent?: 'blue' | 'cyan' | 'purple' | 'green' | 'amber'
  loading?: boolean
  index?: number
}

const ACCENT_MAP: Record<NonNullable<KpiCardProps['accent']>, string> = {
  blue: 'from-chart-1/20 to-transparent text-chart-1',
  cyan: 'from-chart-2/20 to-transparent text-chart-2',
  purple: 'from-chart-3/20 to-transparent text-chart-3',
  green: 'from-chart-4/20 to-transparent text-chart-4',
  amber: 'from-chart-5/20 to-transparent text-chart-5',
}

export function KpiCard({
  label,
  value,
  icon: Icon,
  delta,
  accent = 'blue',
  loading,
  index = 0,
}: KpiCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="space-y-3 p-5">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-9 w-9 rounded-lg" />
          </div>
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-3 w-16" />
        </CardContent>
      </Card>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: 'easeOut' }}
    >
      <Card className="group relative overflow-hidden transition-transform hover:-translate-y-0.5">
        <div
          className={cn(
            'pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br opacity-70 blur-2xl transition-opacity group-hover:opacity-100',
            ACCENT_MAP[accent],
          )}
        />
        <CardContent className="relative space-y-3 p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <span
              className={cn(
                'flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br',
                ACCENT_MAP[accent],
              )}
            >
              <Icon className="h-4.5 w-4.5" />
            </span>
          </div>
          <p className="text-3xl font-bold tracking-tight tabular-nums">{value}</p>
          {delta && (
            <p
              className={cn(
                'inline-flex items-center gap-1 text-xs font-medium',
                delta.positive === false ? 'text-destructive' : 'text-success',
              )}
            >
              {delta.direction === 'up' ? (
                <ArrowUpRight className="h-3.5 w-3.5" />
              ) : (
                <ArrowDownRight className="h-3.5 w-3.5" />
              )}
              {delta.value}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
