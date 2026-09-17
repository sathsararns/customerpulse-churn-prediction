import { useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { AppShell } from '@/components/layout/app-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ModelInfoPanel } from '@/components/dashboard/model-info-panel'
import { PipelineHealth } from '@/components/dashboard/pipeline-health'
import { useApiResource } from '@/hooks/use-api-resource'
import { getModelInfo } from '@/services/api'

export function ModelInfoPage() {
  const fetcher = useCallback(() => getModelInfo(), [])
  const { data: info, isLive, loading, refetch } = useApiResource(fetcher)

  return (
    <AppShell
      title="Model Info"
      description="Deployment details and pipeline health for the active model"
      isLive={loading ? undefined : isLive}
      actions={
        <Button variant="outline" size="sm" onClick={refetch} disabled={loading}>
          <RefreshCw className={loading ? 'animate-spin' : undefined} />
          Refresh
        </Button>
      }
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ModelInfoPanel info={info} loading={loading} />

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Pipeline health</CardTitle>
            <CardDescription>End-to-end status of the training and deployment pipeline</CardDescription>
          </CardHeader>
          <CardContent>
            <PipelineHealth loading={loading} />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
