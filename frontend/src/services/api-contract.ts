import type { PredictionResponse, RecentPrediction, RiskLevel } from '../types/index.ts'
import { getRecommendedAction } from '../lib/risk.ts'

/** Demo mode is explicit. Live request failures always reach the caller. */
export async function requestResource<T>(
  call: () => Promise<T>,
  demo: () => T,
  demoMode: boolean,
): Promise<{ data: T; isLive: boolean }> {
  if (demoMode) return { data: demo(), isLive: false }
  return { data: await call(), isLive: true }
}

export function validatePrediction(data: PredictionResponse): PredictionResponse {
  if (
    !data.model_version || !data.model ||
    !['Low', 'Medium', 'High'].includes(data.risk_level) ||
    !['Churn', 'Not Churn'].includes(data.prediction) ||
    !Number.isFinite(data.probability) || data.probability < 0 || data.probability > 1
  ) throw new Error('The API returned an incomplete prediction')
  return data
}

export interface BackendRecentPrediction {
  event_id?: string
  customer_id?: string | null
  source?: 'api' | 'batch' | 'stream' | 'legacy'
  id: number
  created_at: string
  model_name: string
  model_version: string | null
  prediction: 'Churn' | 'Not Churn'
  probability: number
  risk_level: RiskLevel
  customer_payload: Record<string, unknown>
}

export function mapRecentPrediction(item: BackendRecentPrediction): RecentPrediction {
  const gender = item.customer_payload.gender
  const tenure = item.customer_payload.tenure
  return {
    id: String(item.id),
    customerId: item.customer_id ?? 'Customer ID not provided',
    eventId: item.event_id,
    source: item.source,
    customerName: typeof gender === 'string' && typeof tenure === 'number'
      ? `${gender} customer / ${tenure}m` : `Customer #${item.id}`,
    churnRisk: item.risk_level,
    modelVersion: item.model_version,
    probability: item.probability,
    prediction: item.prediction,
    timestamp: item.created_at,
    action: getRecommendedAction(item.risk_level),
  }
}
