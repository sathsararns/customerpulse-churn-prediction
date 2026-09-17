import { Cpu, Database, GitBranch, HeartPulse, History, Layers } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/dashboard/status-badge'
import { formatRelativeTime } from '@/lib/utils'
import type { ModelInfo } from '@/types'

interface ModelInfoPanelProps {
  info: ModelInfo | null
  loading: boolean
}

export function ModelInfoPanel({ info, loading }: ModelInfoPanelProps) {
  if (loading || !info) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            Model Info
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  const rows = [
    { icon: GitBranch, label: 'Version', value: info.version },
    { icon: History, label: 'Last updated', value: formatRelativeTime(info.lastUpdated) },
    { icon: Database, label: 'Training set size', value: `${info.datasetSize.toLocaleString()} rows` },
    { icon: Layers, label: 'Feature count', value: `${info.features} features` },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-primary" />
          Model Info
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-semibold leading-tight">{info.name}</p>
          <p className="text-xs text-muted-foreground">{info.algorithm}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={info.trainingStatus} />
          <StatusBadge status={info.pipelineHealth} />
        </div>

        <Separator />

        <dl className="space-y-3">
          {rows.map((row) => (
            <div key={row.label} className="flex items-center justify-between text-sm">
              <dt className="flex items-center gap-2 text-muted-foreground">
                <row.icon className="h-3.5 w-3.5" />
                {row.label}
              </dt>
              <dd className="font-medium tabular-nums">{row.value}</dd>
            </div>
          ))}
        </dl>

        <Separator />

        <div className="flex items-center gap-2 rounded-lg bg-success/10 px-3 py-2.5 text-xs font-medium text-success">
          <HeartPulse className="h-4 w-4" />
          Pipeline running nominally — no drift detected
        </div>
      </CardContent>
    </Card>
  )
}
