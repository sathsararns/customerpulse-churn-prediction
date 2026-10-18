import { useState } from 'react'
import { toast } from 'sonner'
import { AppShell } from '@/components/layout/app-shell'
import { PredictionForm } from '@/components/forms/prediction-form'
import { PredictionResultPanel } from '@/components/dashboard/prediction-result-panel'
import { apiErrorMessage, postPrediction, notifyRecentPredictionsChanged } from '@/services/api'
import { ResourceError } from '@/components/dashboard/resource-error'
import type { PredictionRequest, PredictionResponse } from '@/types'

export function PredictPage() {
  const [result, setResult] = useState<PredictionResponse | null>(null)
  const [lastPayload, setLastPayload] = useState<PredictionRequest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [isLive, setIsLive] = useState<boolean | undefined>(undefined)

  async function handleSubmit(payload: PredictionRequest) {
    setLastPayload(payload)
    setSubmitting(true)
    setResult(null)
    setError(null)
    try {
      const { data, isLive: live } = await postPrediction(payload)
      setResult(data)
      setIsLive(live)

      if (live) {
        notifyRecentPredictionsChanged()
      }

      const risk = data.risk_level
      if (!live) {
        toast.warning('Demo prediction generated', {
          description: 'Explicit demo mode is enabled; this is an illustrated estimate.',
        })
      } else if (risk === 'High') {
        toast.error('High churn risk detected', {
          description: 'Consider escalating this customer to the retention team.',
        })
      } else {
        toast.success('Prediction complete', {
          description: `Model returned ${data.prediction} at ${(data.probability * 100).toFixed(1)}% probability.`,
        })
      }
    } catch (cause) {
      setIsLive(false)
      const message = apiErrorMessage(cause)
      setError(message)
      toast.error('Prediction failed', {
        description: message,
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell
      title="Predict Churn"
      description="Score a customer profile against the production churn model"
      isLive={isLive}
    >
      {error && <div className="mb-5"><ResourceError message={error} onRetry={() => { if (lastPayload) void handleSubmit(lastPayload) }} /></div>}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
        <PredictionForm onSubmit={handleSubmit} submitting={submitting} />
        <PredictionResultPanel result={result} loading={submitting} />
      </div>
    </AppShell>
  )
}
