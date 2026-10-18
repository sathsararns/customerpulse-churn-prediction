import { AlertCircle, CheckCircle2, Circle, CircleDot, MinusCircle } from 'lucide-react'
import { useApiResource } from '@/hooks/use-api-resource'
import { getPipelineStatus } from '@/services/api'
import { ResourceError } from '@/components/dashboard/resource-error'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/utils'

export function PipelineHealth() {
  const { data, loading, error, refetch } = useApiResource(getPipelineStatus, 10000)
  if (loading) return <Skeleton className="h-40 w-full" />
  if (error) return <ResourceError message={error} onRetry={refetch} />
  const run = data?.run
  if (!run) return <p className="text-sm text-muted-foreground">No training run has been recorded yet. New training runs will appear here.</p>
  return (
    <div className="space-y-4">
      <div className="space-y-1 text-sm">
        <p>Latest run: <strong>{run.status}</strong></p>
        <p className="break-all text-xs text-muted-foreground">{run.model_version}</p>
        <p className="text-xs text-muted-foreground">Started {formatRelativeTime(run.started_at)}</p>
      </div>
      {run.error && <p role="alert" className="text-sm text-destructive">{run.error}</p>}
      <ol className="space-y-4">
        {run.stages.map((stage) => {
          const Icon = stage.status === 'completed' ? CheckCircle2 : stage.status === 'running' ? CircleDot : stage.status === 'failed' ? AlertCircle : stage.status === 'skipped' ? MinusCircle : Circle
          return (
            <li key={stage.id} className="flex gap-3">
              <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', stage.status === 'completed' ? 'text-success' : stage.status === 'failed' ? 'text-destructive' : 'text-muted-foreground', stage.status === 'running' && 'animate-pulse')} />
              <div><p className="text-sm font-medium">{stage.label} <span className="font-normal text-muted-foreground">&middot; {stage.status}</span></p>
                {stage.message && <p className="text-xs text-muted-foreground">{stage.message}</p>}
              </div>
            </li>
          )
        })}
      </ol>
      <p className="break-all text-xs text-muted-foreground">Serving: {data?.serving_model_version ?? 'No model loaded'}</p>
    </div>
  )
}
