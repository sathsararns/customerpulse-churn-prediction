import { useState } from 'react'
import { toast } from 'sonner'
import { AppShell } from '@/components/layout/app-shell'
import { PredictionForm } from '@/components/forms/prediction-form'
import { PredictionResultPanel } from '@/components/dashboard/prediction-result-panel'
import { postPrediction } from '@/services/api'
import { getRiskLevel } from '@/lib/risk'
import type { PredictionRequest, PredictionResponse } from '@/types'

export function PredictPage() {
  const [result, setResult] = useState<PredictionResponse | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [isLive, setIsLive] = useState<boolean | undefined>(undefined)

  async function handleSubmit(payload: PredictionRequest) {
    setSubmitting(true)
    setResult(null)
    try {
      const { data, isLive: live } = await postPrediction(payload)
      setResult(data)
      setIsLive(live)
      const risk = getRiskLevel(data.probability)
      if (!live) {
        toast.warning('Prediction generated from demo data', {
          description: 'The /predict endpoint is unreachable — showing a heuristic estimate instead.',
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
    } catch {
      toast.error('Prediction failed', {
        description: 'Something went wrong while scoring this customer. Please try again.',
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
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
        <PredictionForm onSubmit={handleSubmit} submitting={submitting} />
        <PredictionResultPanel result={result} loading={submitting} />
      </div>
    </AppShell>
  )
}
