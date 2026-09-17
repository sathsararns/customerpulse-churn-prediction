import { useCallback, useMemo, useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import { AppShell } from '@/components/layout/app-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { RecentPredictionsTable } from '@/components/dashboard/recent-predictions-table'
import { useApiResource } from '@/hooks/use-api-resource'
import { getRecentPredictions } from '@/services/api'

export function ActivityPage() {
  const fetcher = useCallback(() => getRecentPredictions(), [])
  const { data: predictions, isLive, loading, refetch } = useApiResource(fetcher)
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!predictions) return []
    const q = query.trim().toLowerCase()
    if (!q) return predictions
    return predictions.filter(
      (p) => p.customerName.toLowerCase().includes(q) || p.customerId.toLowerCase().includes(q),
    )
  }, [predictions, query])

  return (
    <AppShell
      title="Recent Activity"
      description="Latest churn predictions scored by the model"
      isLive={loading ? undefined : isLive}
      actions={
        <Button variant="outline" size="sm" onClick={refetch} disabled={loading}>
          <RefreshCw className={loading ? 'animate-spin' : undefined} />
          Refresh
        </Button>
      }
    >
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Prediction history</CardTitle>
            <CardDescription>{predictions?.length ?? 0} records in the current window</CardDescription>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search customer or ID…"
              className="pl-9"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          <RecentPredictionsTable predictions={filtered} loading={loading} />
        </CardContent>
      </Card>
    </AppShell>
  )
}
