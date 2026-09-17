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
        <RadialBarChart
          data={data}
          startAngle={90}
          endAngle={-270}
          innerRadius="72%"
          outerRadius="100%"
        >
          <defs>
            <linearGradient id="radialBrand" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="hsl(217 91% 60%)" />
              <stop offset="50%" stopColor="hsl(189 94% 48%)" />
              <stop offset="100%" stopColor="hsl(262 83% 70%)" />
            </linearGradient>
          </defs>
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background={{ fill: 'hsl(var(--muted))' }} dataKey="value" cornerRadius={12} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold tabular-nums">{pct}%</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}
