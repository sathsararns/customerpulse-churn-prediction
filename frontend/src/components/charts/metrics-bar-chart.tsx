import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ModelMetrics } from '@/types'

interface MetricsBarChartProps {
  metrics: ModelMetrics
}

// Validated categorical palette (colorblind-safe, see dataviz skill) — one hue per metric
const COLORS = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)', 'var(--series-5)']

export function MetricsBarChart({ metrics }: MetricsBarChartProps) {
  const data = [
    { name: 'Accuracy', value: Number((metrics.accuracy * 100).toFixed(1)) },
    { name: 'Precision', value: Number((metrics.precision * 100).toFixed(1)) },
    { name: 'Recall', value: Number((metrics.recall * 100).toFixed(1)) },
    { name: 'F1 Score', value: Number((metrics.f1_score * 100).toFixed(1)) },
    { name: 'ROC-AUC', value: Number((metrics.roc_auc * 100).toFixed(1)) },
  ]

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 24, right: 8, left: -12, bottom: 0 }} barCategoryGap="32%">
        <defs>
          {data.map((entry, index) => (
            <linearGradient key={entry.name} id={`bar-gradient-${index}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS[index % COLORS.length]} stopOpacity={1} />
              <stop offset="100%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.72} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border) / 0.6)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
          axisLine={{ stroke: 'hsl(var(--border))' }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          cursor={{ fill: 'hsl(var(--muted) / 0.5)', radius: 8 }}
          contentStyle={{
            background: 'hsl(var(--popover))',
            border: '1px solid hsl(var(--border))',
            borderRadius: 10,
            boxShadow: '0 8px 24px -8px rgb(0 0 0 / 0.25)',
            fontSize: 12,
            color: 'hsl(var(--popover-foreground))',
          }}
          formatter={(value) => [`${value}%`, 'Score']}
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]} maxBarSize={44}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={`url(#bar-gradient-${index})`} />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            offset={10}
            fill="hsl(var(--foreground))"
            fontSize={12}
            fontWeight={600}
            formatter={(v) => `${v}%`}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
