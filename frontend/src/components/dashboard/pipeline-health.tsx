import { motion } from 'framer-motion'
import { CheckCircle2, CircleDot, Database, FlaskConical, Rocket, ShieldCheck } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface PipelineStage {
  label: string
  description: string
  icon: typeof Database
  status: 'complete' | 'active' | 'pending'
}

const STAGES: PipelineStage[] = [
  { label: 'Data ingestion', description: 'Raw churn dataset validated and loaded', icon: Database, status: 'complete' },
  { label: 'Feature engineering', description: 'Encoding, scaling, and outlier handling applied', icon: FlaskConical, status: 'complete' },
  { label: 'Model training', description: 'Logistic regression fit on training split', icon: ShieldCheck, status: 'complete' },
  { label: 'Evaluation', description: 'Metrics computed on holdout test set', icon: CheckCircle2, status: 'complete' },
  { label: 'Deployment', description: 'Model artifact served via inference pipeline', icon: Rocket, status: 'active' },
]

export function PipelineHealth({ loading }: { loading?: boolean }) {
  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  return (
    <ol className="relative space-y-1 pl-1">
      {STAGES.map((stage, i) => (
        <motion.li
          key={stage.label}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, delay: i * 0.07 }}
          className="relative flex gap-4 pb-6 last:pb-0"
        >
          {i < STAGES.length - 1 && (
            <span
              className={cn(
                'absolute left-[15px] top-8 h-full w-px',
                stage.status === 'complete' ? 'bg-success/40' : 'bg-border',
              )}
            />
          )}
          <span
            className={cn(
              'relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border',
              stage.status === 'complete' && 'border-success/30 bg-success/15 text-success',
              stage.status === 'active' && 'border-primary/30 bg-primary/15 text-primary',
              stage.status === 'pending' && 'border-border bg-muted text-muted-foreground',
            )}
          >
            {stage.status === 'active' ? (
              <CircleDot className="h-4 w-4 animate-pulse" />
            ) : (
              <stage.icon className="h-4 w-4" />
            )}
          </span>
          <div className="pt-1">
            <p className="text-sm font-semibold">{stage.label}</p>
            <p className="text-xs text-muted-foreground">{stage.description}</p>
          </div>
        </motion.li>
      ))}
    </ol>
  )
}
