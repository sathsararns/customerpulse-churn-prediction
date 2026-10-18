import { ExternalLink, FlaskConical, RefreshCw, ShieldCheck } from 'lucide-react'
import { AppShell } from '@/components/layout/app-shell'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ResourceError } from '@/components/dashboard/resource-error'
import { PipelineHealth } from '@/components/dashboard/pipeline-health'
import { useApiResource } from '@/hooks/use-api-resource'
import { DEMO_MODE, getMetrics, getMlflowInfo, getModelInfo } from '@/services/api'
import { formatPercent } from '@/lib/utils'

export function ModelInfoPage() {
  const model = useApiResource(getModelInfo, 15000)
  const metrics = useApiResource(getMetrics, 15000)
  const tracking = useApiResource(getMlflowInfo, 10000)
  const compatible = metrics.data && model.data && metrics.data.model_version === model.data.version
  const connected = tracking.data?.status === 'connected'
  const refresh = () => { void model.refetch(); void metrics.refetch(); void tracking.refetch() }
  return (
    <AppShell title="Model Info" description="Loaded model, recorded training state, and tracking connectivity"
      isLive={model.loading ? undefined : model.isLive}
      actions={<Button variant="outline" size="sm" onClick={refresh}><RefreshCw />Refresh</Button>}>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" />Serving model</CardTitle><CardDescription>The version loaded by the API at startup</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {model.error ? <ResourceError message={model.error} onRetry={model.refetch} /> : <>
              <p className="text-lg font-semibold">{model.data?.name ?? 'Loading...'}</p>
              <p className="break-all text-xs text-muted-foreground">Version: {model.data?.version ?? 'Loading...'}</p>
              <p className="text-sm">Decision threshold: {model.data ? formatPercent(model.data.predictionThreshold) : '--'}</p>
              {metrics.error ? <ResourceError message={metrics.error} onRetry={metrics.refetch} /> : compatible ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {(['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc'] as const).map((key) => (
                    <div key={key} className="rounded-xl border p-3"><p className="text-xs uppercase text-muted-foreground">{key.replaceAll('_', ' ')}</p><p className="mt-1 font-semibold">{formatPercent(metrics.data![key], 2)}</p></div>
                  ))}
                </div>
              ) : <p className="text-sm text-muted-foreground">{metrics.loading || model.loading ? 'Loading matching metrics...' : 'Model and metric versions differ. Refresh the details.'}</p>}
            </>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><FlaskConical className="h-5 w-5" />MLflow tracking store</CardTitle><CardDescription>Connectivity checked by the backend</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {tracking.error ? <ResourceError message={tracking.error} onRetry={tracking.refetch} /> : <>
              <div className="flex items-center justify-between gap-3"><p className="font-semibold">{tracking.data?.experiment_name ?? 'Checking...'}</p><Badge variant={connected ? 'default' : 'secondary'}>{DEMO_MODE ? 'Demo' : tracking.loading ? 'Checking' : connected ? 'Connected' : 'Disconnected'}</Badge></div>
              <p className="break-all text-xs text-muted-foreground">{tracking.data?.tracking_uri}</p>
              <p className="text-sm">{tracking.data?.detail}</p>
              {tracking.data && <Button asChild variant="outline"><a href={tracking.data.ui_url} target="_blank" rel="noreferrer">Open MLflow UI<ExternalLink className="h-4 w-4" /></a></Button>}
            </>}
          </CardContent>
        </Card>
      </div>
      <Card className="mt-6"><CardHeader><CardTitle>Recorded pipeline run</CardTitle><CardDescription>Observed stages from the most recent training command</CardDescription></CardHeader><CardContent><PipelineHealth /></CardContent></Card>
    </AppShell>
  )
}
