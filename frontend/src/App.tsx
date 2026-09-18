import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import { Loader2 } from 'lucide-react'
import { ThemeProvider } from '@/context/theme-provider'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ScrollToTop } from '@/components/layout/scroll-to-top'

const LandingPage = lazy(() => import('@/pages/landing').then((m) => ({ default: m.LandingPage })))
const PredictPage = lazy(() => import('@/pages/predict').then((m) => ({ default: m.PredictPage })))
const MetricsPage = lazy(() => import('@/pages/metrics').then((m) => ({ default: m.MetricsPage })))
const ActivityPage = lazy(() => import('@/pages/activity').then((m) => ({ default: m.ActivityPage })))
const ModelInfoPage = lazy(() =>
  import('@/pages/model-info').then((m) => ({ default: m.ModelInfoPage })),
)

function RouteFallback() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={200}>
        <ScrollToTop />
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/app" element={<Navigate to="/app/predict" replace />} />
            <Route path="/app/predict" element={<PredictPage />} />
            <Route path="/app/metrics" element={<MetricsPage />} />
            <Route path="/app/activity" element={<ActivityPage />} />
            <Route path="/app/model" element={<ModelInfoPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
        <Toaster
          position="top-right"
          toastOptions={{
            classNames: {
              toast: 'rounded-lg border border-border bg-popover text-popover-foreground shadow-card',
            },
          }}
        />
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
