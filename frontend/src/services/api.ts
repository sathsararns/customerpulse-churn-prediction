import axios from 'axios'
import {
  MOCK_HEALTH,
  MOCK_METRICS,
  MOCK_MODEL_INFO,
  MOCK_RECENT_PREDICTIONS,
} from '@/data/mockData'
import type {
  HealthStatus,
  ModelInfo,
  ModelMetrics,
  PredictionRequest,
  PredictionResponse,
  RecentPrediction,
} from '@/types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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
  // Backend contract: GET /health -> { status: "ok" | "degraded" | "down" }.
  // Only "ok" counts as live; anything else falls back to demo data.
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
  // Falls back to the last recorded evaluation report
  // (backend/reports/evaluation_report.json) if the backend is unreachable.
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

export async function getRecentPredictions() {
  // TODO(backend): GET /recent-predictions is not yet implemented server-side.
  return withFallback(
    async () => {
      const res = await apiClient.get<RecentPrediction[]>('/recent-predictions')
      return res.data
    },
    MOCK_RECENT_PREDICTIONS,
  )
}

function mockPredictionFor(payload: PredictionRequest): PredictionResponse {
  // Lightweight heuristic mirroring known churn drivers, purely so the demo
  // response reacts sensibly to form input when the backend is offline.
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
