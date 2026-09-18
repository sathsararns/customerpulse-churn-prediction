import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts'

interface PerformanceRadialChartProps {
  value: number
  label: string
}

export function PerformanceRadialChart({ value, label }: PerformanceRadialChartProps) {
  const pct = Math.round(value * 100)
  const data = [{ name: label, value: pct, fill: 'url(#radialBrand)' }]

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={220}>
        <RadialBarChart data={data} startAngle={90} endAngle={-270} innerRadius="80%" outerRadius="100%">
          <defs>
            <linearGradient id="radialBrand" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%" stopColor="var(--series-1)" stopOpacity={0.75} />
              <stop offset="100%" stopColor="var(--series-1)" stopOpacity={1} />
            </linearGradient>
            <filter id="radialGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor="var(--series-1)" floodOpacity="0.35" />
            </filter>
          </defs>
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar
            background={{ fill: 'hsl(var(--muted) / 0.6)' }}
            dataKey="value"
            cornerRadius={10}
            filter="url(#radialGlow)"
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold tabular-nums tracking-tight">{pct}%</span>
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}
