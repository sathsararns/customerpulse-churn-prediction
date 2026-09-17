import { motion } from 'framer-motion'
import { History } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/dashboard/empty-state'
import { RiskBadge } from '@/components/dashboard/risk-badge'
import { formatPercent, formatRelativeTime, initialsFromName } from '@/lib/utils'
import type { RecentPrediction } from '@/types'

interface RecentPredictionsTableProps {
  predictions: RecentPrediction[]
  loading: boolean
}

export function RecentPredictionsTable({ predictions, loading }: RecentPredictionsTableProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (predictions.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No predictions yet"
        description="Run your first prediction from the Predict Churn page to see activity here."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <th className="pb-3 pr-4 font-medium">Customer</th>
            <th className="pb-3 pr-4 font-medium">Prediction</th>
            <th className="pb-3 pr-4 font-medium">Risk</th>
            <th className="pb-3 pr-4 font-medium">Probability</th>
            <th className="pb-3 pr-4 font-medium">Timestamp</th>
            <th className="pb-3 font-medium">Recommended action</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((p, i) => (
            <motion.tr
              key={p.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.04 }}
              className="border-b border-border/60 transition-colors last:border-0 hover:bg-accent/40"
            >
              <td className="py-3 pr-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-brand text-[11px] font-semibold text-white">
                    {initialsFromName(p.customerName)}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{p.customerName}</p>
                    <p className="truncate text-xs text-muted-foreground">{p.customerId}</p>
                  </div>
                </div>
              </td>
              <td className="py-3 pr-4">
                <Badge variant={p.prediction === 'Churn' ? 'destructive' : 'success'}>
                  {p.prediction}
                </Badge>
              </td>
              <td className="py-3 pr-4">
                <RiskBadge level={p.churnRisk} />
              </td>
              <td className="py-3 pr-4 font-medium tabular-nums">{formatPercent(p.probability)}</td>
              <td className="py-3 pr-4 whitespace-nowrap text-muted-foreground">
                {formatRelativeTime(p.timestamp)}
              </td>
              <td className="py-3 text-muted-foreground">{p.action}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
