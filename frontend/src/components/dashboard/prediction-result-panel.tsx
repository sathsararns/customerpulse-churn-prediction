import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Lightbulb, Radar, Sparkles } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/dashboard/empty-state'
import { RiskBadge } from '@/components/dashboard/risk-badge'
import { getRecommendedAction, getRiskLevel } from '@/lib/risk'
import { cn, formatPercent } from '@/lib/utils'
import type { PredictionResponse } from '@/types'

interface PredictionResultPanelProps {
  result: PredictionResponse | null
  loading: boolean
}

export function PredictionResultPanel({ result, loading }: PredictionResultPanelProps) {
  return (
    <Card className="sticky top-24 overflow-hidden">
      <div className="h-1 w-full bg-gradient-brand" />
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Radar className="h-4 w-4 text-primary" />
          Prediction Result
        </CardTitle>
      </CardHeader>
      <CardContent>
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-5"
            >
              <div className="flex flex-col items-center gap-3 py-4">
                <Skeleton className="h-28 w-28 rounded-full" />
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-24" />
              </div>
              <Skeleton className="h-20 w-full rounded-lg" />
            </motion.div>
          ) : !result ? (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <EmptyState
                icon={Sparkles}
                title="No prediction yet"
                description="Fill in the customer profile and run the model to see churn risk, probability, and a recommended action here."
              />
            </motion.div>
          ) : (
            <ResultContent key="result" result={result} />
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  )
}

function ResultContent({ result }: { result: PredictionResponse }) {
  const risk = getRiskLevel(result.probability)
  const isChurn = result.prediction === 'Churn'
  const action = getRecommendedAction(risk)
  const pct = Math.round(result.probability * 100)

  const ringColor = isChurn ? 'stroke-destructive' : 'stroke-success'
  const circumference = 2 * Math.PI * 52

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-6"
    >
      <div className="flex flex-col items-center gap-4 py-2">
        <div className="relative flex h-32 w-32 items-center justify-center">
          <svg viewBox="0 0 120 120" className="h-32 w-32 -rotate-90">
            <circle cx="60" cy="60" r="52" className="fill-none stroke-muted" strokeWidth="8" />
            <motion.circle
              cx="60"
              cy="60"
              r="52"
              className={cn('fill-none', ringColor)}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference - (pct / 100) * circumference }}
              transition={{ duration: 0.9, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className="text-2xl font-bold tabular-nums">{formatPercent(result.probability)}</span>
            <span className="text-[11px] text-muted-foreground">probability</span>
          </div>
        </div>

        <div className="flex flex-col items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold',
              isChurn ? 'bg-destructive/15 text-destructive' : 'bg-success/15 text-success',
            )}
          >
            {isChurn ? <AlertCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
            {result.prediction}
          </span>
          <RiskBadge level={risk} />
        </div>
      </div>

      <div className="rounded-lg border border-border bg-muted/40 p-4">
        <div className="flex items-start gap-2.5">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Recommended action
            </p>
            <p className="mt-1 text-sm leading-relaxed">{action}</p>
          </div>
        </div>
      </div>

      <p className="text-center text-[11px] text-muted-foreground">
        Scored by <span className="font-medium text-foreground">{result.model}</span>
      </p>
    </motion.div>
  )
}
