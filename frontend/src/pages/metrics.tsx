import { useCallback } from 'react'
import { Crosshair, LineChart, RefreshCw, Scale, SearchCheck, Target } from 'lucide-react'
import { AppShell } from '@/components/layout/app-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { KpiCard } from '@/components/dashboard/kpi-card'
import { ConfusionMatrix } from '@/components/dashboard/confusion-matrix'
import { MetricsBarChart } from '@/components/charts/metrics-bar-chart'
import { PerformanceRadialChart } from '@/components/charts/performance-radial-chart'
import { useApiResource } from '@/hooks/use-api-resource'
import { getMetrics } from '@/services/api'
import { formatPercent, formatRelativeTime } from '@/lib/utils'

export function MetricsPage() {
  const fetcher = useCallback(() => getMetrics(), [])
  const { data: metrics, isLive, loading, refetch } = useApiResource(fetcher)

  return (
    <AppShell
      title="Model Metrics"
      description="Evaluation performance for the production churn classifier"
      isLive={loading ? undefined : isLive}
      actions={
        <Button variant="outline" size="sm" onClick={refetch} disabled={loading}>
          <RefreshCw className={loading ? 'animate-spin' : undefined} />
          Refresh
        </Button>
      }
    >
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <KpiCard
            label="Accuracy"
            value={metrics ? formatPercent(metrics.accuracy) : '—'}
            icon={Target}
            accent="blue"
            loading={loading}
            index={0}
          />
          <KpiCard
            label="Precision"
            value={metrics ? formatPercent(metrics.precision) : '—'}
            icon={Crosshair}
            accent="cyan"
            loading={loading}
            index={1}
          />
          <KpiCard
            label="Recall"
            value={metrics ? formatPercent(metrics.recall) : '—'}
            icon={SearchCheck}
            accent="purple"
            loading={loading}
            index={2}
          />
          <KpiCard
            label="F1 Score"
            value={metrics ? formatPercent(metrics.f1_score) : '—'}
            icon={Scale}
            accent="green"
            loading={loading}
            index={3}
          />
          <KpiCard
            label="ROC-AUC"
            value={metrics ? formatPercent(metrics.roc_auc) : '—'}
            icon={LineChart}
            accent="amber"
            loading={loading}
            index={4}
          />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Performance by metric</CardTitle>
              <CardDescription>Comparative view across the five core evaluation metrics</CardDescription>
            </CardHeader>
            <CardContent>
              {loading || !metrics ? (
                <Skeleton className="h-[280px] w-full" />
              ) : (
                <MetricsBarChart metrics={metrics} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>ROC-AUC</CardTitle>
              <CardDescription>Discrimination between churn and non-churn</CardDescription>
            </CardHeader>
            <CardContent>
              {loading || !metrics ? (
                <Skeleton className="h-[220px] w-full rounded-full" />
              ) : (
                <PerformanceRadialChart value={metrics.roc_auc} label="ROC-AUC" />
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Confusion matrix</CardTitle>
              <CardDescription>Predicted vs. actual outcomes on the holdout set</CardDescription>
            </CardHeader>
            <CardContent>
              {loading || !metrics ? (
                <Skeleton className="w-full h-56" />
              ) : (
                <ConfusionMatrix matrix={metrics.confusion_matrix} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Insights</CardTitle>
              <CardDescription>What the numbers mean</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              {loading || !metrics ? (
                <>
                  <Skeleton className="w-full h-4" />
                  <Skeleton className="w-5/6 h-4" />
                  <Skeleton className="w-4/6 h-4" />
                </>
              ) : (
                <>
                  <p>
                    The model correctly classifies{' '}
                    <span className="font-semibold text-foreground">
                      {formatPercent(metrics.accuracy)}
                    </span>{' '}
                    of customers overall, with a strong{' '}
                    <span className="font-semibold text-foreground">
                      {formatPercent(metrics.roc_auc)}
                    </span>{' '}
                    ROC-AUC indicating good separation between churn and retained customers.
                  </p>
                  <p>
                    Precision of {formatPercent(metrics.precision)} means most customers flagged
                    as churn risks genuinely are — recall of {formatPercent(metrics.recall)}{' '}
                    suggests some at-risk customers are still missed and may warrant a lower
                    decision threshold for high-value accounts.
                  </p>
                  <p className="text-xs text-muted-foreground/80">
                    Last evaluated {metrics?.updated_at ? formatRelativeTime(metrics.updated_at) : 'recently'}.
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
