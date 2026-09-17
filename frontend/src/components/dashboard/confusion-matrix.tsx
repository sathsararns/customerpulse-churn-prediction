import { cn } from '@/lib/utils'

interface ConfusionMatrixProps {
  matrix: [[number, number], [number, number]]
}

export function ConfusionMatrix({ matrix }: ConfusionMatrixProps) {
  const [[tn, fp], [fn, tp]] = matrix
  const total = tn + fp + fn + tp
  const max = Math.max(tn, fp, fn, tp)

  const cells = [
    { label: 'True Negative', sub: 'Predicted stay, actually stayed', value: tn, tone: 'success' as const },
    { label: 'False Positive', sub: 'Predicted churn, actually stayed', value: fp, tone: 'warning' as const },
    { label: 'False Negative', sub: 'Predicted stay, actually churned', value: fn, tone: 'destructive' as const },
    { label: 'True Positive', sub: 'Predicted churn, actually churned', value: tp, tone: 'success' as const },
  ]

  const toneClass: Record<string, string> = {
    success: 'bg-success/10 border-success/30 text-success',
    warning: 'bg-warning/10 border-warning/30 text-warning',
    destructive: 'bg-destructive/10 border-destructive/30 text-destructive',
  }

  return (
    <div>
      <div className="mb-3 grid grid-cols-[auto_1fr_1fr] gap-2 text-center text-[11px] font-medium text-muted-foreground">
        <div />
        <div>Predicted: Not Churn</div>
        <div>Predicted: Churn</div>
      </div>
      <div className="grid grid-cols-[auto_1fr_1fr] gap-2">
        <div className="flex flex-col justify-center gap-2 text-[11px] font-medium text-muted-foreground">
          <div className="flex h-24 items-center justify-end pr-2">Actual: Not Churn</div>
          <div className="flex h-24 items-center justify-end pr-2">Actual: Churn</div>
        </div>
        <div className="col-span-2 grid grid-cols-2 gap-2">
          {cells.map((cell) => {
            const intensity = 0.25 + 0.65 * (cell.value / max)
            return (
              <div
                key={cell.label}
                className={cn(
                  'relative flex h-24 flex-col items-center justify-center gap-0.5 rounded-lg border transition-transform hover:scale-[1.02]',
                  toneClass[cell.tone],
                )}
                style={{ opacity: intensity + 0.35 }}
                title={`${cell.label}: ${cell.value}`}
              >
                <span className="text-2xl font-bold tabular-nums">{cell.value.toLocaleString()}</span>
                <span className="px-2 text-center text-[10px] font-medium leading-tight opacity-90">
                  {cell.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
      <p className="mt-3 text-center text-xs text-muted-foreground">
        {total.toLocaleString()} total evaluated samples
      </p>
    </div>
  )
}
