import { useCallback } from 'react'
import { ExternalLink, FlaskConical, ShieldCheck, Sparkles } from 'lucide-react'
import { AppShell } from '@/components/layout/app-shell'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useApiResource } from '@/hooks/use-api-resource'
import { getMetrics, getMlflowInfo, getModelInfo } from '@/services/api'
import { formatPercent } from '@/lib/utils'

export function ModelInfoPage() {
  const modelFetcher = useCallback(() => getModelInfo(), [])
  const metricsFetcher = useCallback(() => getMetrics(), [])
  const mlflowFetcher = useCallback(() => getMlflowInfo(), [])

  const { data: modelInfo, loading: modelLoading, isLive: modelLive } = useApiResource(modelFetcher)
  const { data: metrics, loading: metricsLoading } = useApiResource(metricsFetcher)
  const { data: mlflowInfo, isLive: mlflowLive } = useApiResource(mlflowFetcher)

  return (
    <AppShell
      title="Model Info"
      description="Model summary, training metrics, and MLflow tracking details"
      isLive={modelLoading ? undefined : modelLive}
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              Production model
            </CardTitle>
            <CardDescription>Best model selected from the training pipeline</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-xl border p-4">
              <div>
                <p className="text-sm text-muted-foreground">Model name</p>
                <p className="text-lg font-semibold">
                  {modelLoading ? 'Loading...' : (modelInfo?.name ?? '—')}
                </p>
              </div>
              <Badge variant={modelLive ? 'default' : 'secondary'}>{modelLive ? 'Live' : 'Demo'}</Badge>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <MetricTile
                label="Accuracy"
                value={metrics && !metricsLoading ? formatPercent(metrics.accuracy, 2) : '—'}
              />
              <MetricTile
                label="Precision"
                value={metrics && !metricsLoading ? formatPercent(metrics.precision, 2) : '—'}
              />
              <MetricTile
                label="Recall"
                value={metrics && !metricsLoading ? formatPercent(metrics.recall, 2) : '—'}
              />
              <MetricTile
                label="F1 Score"
                value={metrics && !metricsLoading ? formatPercent(metrics.f1_score, 2) : '—'}
              />
              <MetricTile
                label="ROC AUC"
                value={metrics && !metricsLoading ? formatPercent(metrics.roc_auc, 2) : '—'}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5" />
              MLflow tracking
            </CardTitle>
            <CardDescription>Experiment tracking for training runs and metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-xl border p-4">
              <div>
                <p className="text-sm text-muted-foreground">Experiment</p>
                <p className="text-lg font-semibold">{mlflowInfo?.experiment_name ?? 'Loading...'}</p>
              </div>
              <Badge variant={mlflowLive ? 'default' : 'secondary'}>{mlflowLive ? 'Tracked' : 'Offline'}</Badge>
            </div>

            <div className="space-y-2 rounded-xl border p-4 text-sm">
              <p>
                <span className="text-muted-foreground">Tracking URI:</span> {mlflowInfo?.tracking_uri ?? '—'}
              </p>
              <p>
                <span className="text-muted-foreground">Status:</span> {mlflowInfo?.status ?? '—'}
              </p>
            </div>

            <Button asChild className="w-full">
              <a href={mlflowInfo?.ui_url ?? 'http://127.0.0.1:5000'} target="_blank" rel="noreferrer">
                Open MLflow UI <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            What this model is optimized for
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <InfoPill title="Churn scoring" text="Predicts customers likely to leave." />
          <InfoPill title="Retention action" text="Supports proactive outreach." />
          <InfoPill title="Tracked runs" text="Each training run is logged in MLflow." />
        </CardContent>
      </Card>
    </AppShell>
  )
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
    </div>
  )
}

function InfoPill({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border p-4">
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{text}</p>
    </div>
  )
}
