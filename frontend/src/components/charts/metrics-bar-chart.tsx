import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ModelMetrics } from '@/types'

interface MetricsBarChartProps {
  metrics: ModelMetrics
}

const COLORS = ['hsl(217 91% 60%)', 'hsl(189 94% 48%)', 'hsl(262 83% 70%)', 'hsl(152 60% 45%)', 'hsl(38 92% 55%)']

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
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="28%">
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
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
          cursor={{ fill: 'hsl(var(--muted) / 0.5)' }}
          contentStyle={{
            background: 'hsl(var(--popover))',
            border: '1px solid hsl(var(--border))',
            borderRadius: 8,
            fontSize: 12,
            color: 'hsl(var(--popover-foreground))',
          }}
          formatter={(value) => [`${value}%`, 'Score']}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={48}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
