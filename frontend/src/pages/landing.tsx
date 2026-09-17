import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  Gauge,
  Radio,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { formatPercent } from '@/lib/utils'
import { MOCK_METRICS } from '@/data/mockData'

const STATS = [
  { label: 'Model accuracy', value: formatPercent(MOCK_METRICS.accuracy), icon: TrendingUp },
  { label: 'ROC-AUC score', value: formatPercent(MOCK_METRICS.roc_auc), icon: BarChart3 },
  { label: 'Customers scored', value: '7,043', icon: Users },
  { label: 'Avg. response time', value: '180ms', icon: Zap },
]

const FEATURES = [
  {
    icon: Gauge,
    title: 'Real-time churn scoring',
    description: 'Score any customer profile instantly against the production model with full probability breakdowns.',
  },
  {
    icon: BarChart3,
    title: 'Live model analytics',
    description: 'Track accuracy, precision, recall, F1, and ROC-AUC alongside a full confusion matrix at a glance.',
  },
  {
    icon: ShieldCheck,
    title: 'Actionable risk tiers',
    description: 'Every prediction ships with a Low / Medium / High risk tier and a recommended retention action.',
  },
]

export function LandingPage() {
  return (
    <div className="relative min-h-svh overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 bg-gradient-radial-glow" />
      <div className="pointer-events-none absolute inset-0 bg-grid-slate bg-[size:56px_56px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]" />

      <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-brand shadow-glow">
            <Radio className="h-4.5 w-4.5 text-white" />
          </span>
          <span className="text-sm font-bold tracking-tight">
            CustomerPulse <span className="text-gradient-brand">AI</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" asChild className="hidden sm:inline-flex">
            <Link to="/app/metrics">Analytics</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/app/predict">Open dashboard</Link>
          </Button>
          <ThemeToggle />
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-6 pb-24 pt-10 sm:pt-16">
        <div className="mx-auto max-w-3xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Production ML inference, live from your FastAPI backend
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.05 }}
            className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl"
          >
            Know who's leaving —{' '}
            <span className="text-gradient-brand">before they do.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.12 }}
            className="mx-auto mt-5 max-w-xl text-balance text-base text-muted-foreground sm:text-lg"
          >
            CustomerPulse AI turns your churn model into a decision-ready workspace for
            operations and analyst teams — predict, monitor, and act in one place.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.18 }}
            className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <Button size="lg" variant="brand" asChild className="w-full sm:w-auto">
              <Link to="/app/predict">
                <Zap />
                Predict Churn
                <ArrowRight />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild className="w-full sm:w-auto">
              <Link to="/app/metrics">
                <BarChart3 />
                View Analytics
              </Link>
            </Button>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mx-auto mt-16 grid max-w-4xl grid-cols-2 gap-4 lg:grid-cols-4"
        >
          {STATS.map((stat) => (
            <Card key={stat.label} className="border-border/60 bg-card/60 backdrop-blur">
              <CardContent className="flex flex-col items-center gap-2 p-5 text-center">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <stat.icon className="h-4 w-4" />
                </span>
                <span className="text-2xl font-bold tabular-nums">{stat.value}</span>
                <span className="text-xs text-muted-foreground">{stat.label}</span>
              </CardContent>
            </Card>
          ))}
        </motion.div>

        <div className="mx-auto mt-24 grid max-w-5xl gap-6 sm:grid-cols-3">
          {FEATURES.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              <Card className="h-full">
                <CardContent className="space-y-3 p-6">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-brand text-white shadow-glow">
                    <feature.icon className="h-5 w-5" />
                  </span>
                  <h3 className="text-base font-semibold">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 border-t border-border py-6 text-center text-xs text-muted-foreground">
        CustomerPulse AI — internal churn intelligence dashboard.
      </footer>
    </div>
  )
}
