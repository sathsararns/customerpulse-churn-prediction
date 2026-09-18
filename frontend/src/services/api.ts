import axios from 'axios'
import {
  MOCK_HEALTH,
  MOCK_METRICS,
  MOCK_MODEL_INFO,
  MOCK_RECENT_PREDICTIONS,
} from '@/data/mockData'
import { getRecommendedAction, getRiskLevel } from '@/lib/risk'
import type {
  HealthStatus,
  ModelInfo,
  ModelMetrics,
  PredictionRequest,
  PredictionResponse,
  RecentPrediction,
  RiskLevel,
} from '@/types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const RECENT_PREDICTIONS_REFRESH_EVENT = 'customerpulse:recent-predictions-refresh'

export function notifyRecentPredictionsChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(RECENT_PREDICTIONS_REFRESH_EVENT))
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
})

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Wraps a real API call and falls back to mock data if the backend is
 * unreachable or the endpoint isn't implemented yet. Every call site marks
 * `isLive` so the UI can surface a "Demo data" indicator honestly.
 */
async function withFallback<T>(
  call: () => Promise<T>,
  mock: T,
  minDelay = 350,
): Promise<{ data: T; isLive: boolean }> {
  try {
    const [data] = await Promise.all([call(), delay(minDelay)])
    return { data, isLive: true }
  } catch {
    await delay(minDelay)
    return { data: mock, isLive: false }
  }
}

export async function getHealth() {
  return withFallback(
    async () => {
      const res = await apiClient.get<HealthStatus>('/health')
      if (res.data.status !== 'ok') {
        throw new Error('Backend reported non-ok health status')
      }
      return res.data
    },
    MOCK_HEALTH,
    200,
  )
}

export async function postPrediction(payload: PredictionRequest) {
  return withFallback(
    async () => {
      const res = await apiClient.post<PredictionResponse>('/predict', payload)
      return res.data
    },
    mockPredictionFor(payload),
    900,
  )
}

export async function getMetrics() {
  return withFallback(
    async () => {
      const res = await apiClient.get<ModelMetrics>('/metrics')
      return res.data
    },
    MOCK_METRICS,
  )
}

export async function getModelInfo() {
  return withFallback(
    async () => {
      const res = await apiClient.get<ModelInfo>('/model-info')
      return res.data
    },
    MOCK_MODEL_INFO,
  )
}

type BackendRecentPredictionItem = {
  id: number
  created_at: string
  model_name: string
  prediction: 'Churn' | 'Not Churn'
  probability: number
  risk_level: RiskLevel
  customer_payload: Record<string, unknown>
}

type BackendRecentPredictionsResponse = {
  items: BackendRecentPredictionItem[]
}

function mapBackendRecentPrediction(item: BackendRecentPredictionItem): RecentPrediction {
  const customerId = `PRED-${String(item.id).padStart(4, '0')}`

  const gender = typeof item.customer_payload.gender === 'string' ? item.customer_payload.gender : null
  const tenure = typeof item.customer_payload.tenure === 'number' ? item.customer_payload.tenure : null
  const customerName =
    gender && tenure !== null
      ? `${gender} customer · ${tenure}m`
      : `Customer #${item.id}`

  const risk = item.risk_level ?? getRiskLevel(item.probability)

  return {
    id: String(item.id),
    customerId,
    customerName,
    churnRisk: risk,
    probability: item.probability,
    prediction: item.prediction,
    timestamp: item.created_at,
    action: getRecommendedAction(risk),
  }
}

export async function getRecentPredictions() {
  return withFallback(
    async () => {
      const res = await apiClient.get<BackendRecentPredictionsResponse>('/recent-predictions')
      const items = Array.isArray(res.data.items) ? res.data.items : []
      return items.map(mapBackendRecentPrediction)
    },
    MOCK_RECENT_PREDICTIONS,
  )
}

function mockPredictionFor(payload: PredictionRequest): PredictionResponse {
  let score = 0.18

  if (payload.Contract === 'Month-to-month') score += 0.22
  if (payload.Contract === 'One year') score += 0.05

  if (payload.InternetService === 'Fiber optic') score += 0.12
  if (payload.tenure < 12) score += 0.18
  else if (payload.tenure > 48) score -= 0.15

  if (payload.PaymentMethod === 'Electronic check') score += 0.1
  if (payload.OnlineSecurity !== 'Yes') score += 0.06
  if (payload.TechSupport !== 'Yes') score += 0.06
  if (payload.PaperlessBilling === 'Yes') score += 0.03
  if (payload.SeniorCitizen === 1) score += 0.04
  if (payload.Partner === 'No' && payload.Dependents === 'No') score += 0.03
  if (payload.MonthlyCharges > 80) score += 0.05

  const probability = Math.min(0.97, Math.max(0.02, score))

  return {
    prediction: probability >= 0.5 ? 'Churn' : 'Not Churn',
    probability: Number(probability.toFixed(4)),
    model: 'demo-heuristic',
  }
}