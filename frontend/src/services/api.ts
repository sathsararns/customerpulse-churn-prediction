import axios from 'axios'
import {
  MOCK_HEALTH, MOCK_METRICS, MOCK_MLFLOW_INFO, MOCK_MODEL_INFO,
  MOCK_RECENT_PREDICTIONS, MOCK_PIPELINE_STATUS,
} from '@/data/mockData'
import { getRiskLevel } from '@/lib/risk'
import { mapRecentPrediction, requestResource, validatePrediction } from './api-contract'
import type { BackendRecentPrediction } from './api-contract'
import type {
  HealthStatus, MlflowInfo, ModelInfo, ModelMetrics, PipelineStatus,
  PredictionRequest, PredictionResponse,
} from '@/types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'
export const RECENT_PREDICTIONS_REFRESH_EVENT = 'customerpulse:recent-predictions-refresh'
export const apiClient = axios.create({ baseURL: API_BASE_URL, timeout: 8000 })

export function notifyRecentPredictionsChanged() {
  window.dispatchEvent(new Event(RECENT_PREDICTIONS_REFRESH_EVENT))
}

function resource<T>(call: () => Promise<T>, demo: () => T) {
  return requestResource(call, demo, DEMO_MODE)
}

export function getHealth() {
  return resource(async () => (await apiClient.get<HealthStatus>('/health')).data, () => MOCK_HEALTH)
}

export function postPrediction(payload: PredictionRequest) {
  return resource(async () => validatePrediction(
    (await apiClient.post<PredictionResponse>('/predict', payload)).data,
  ), () => mockPredictionFor(payload))
}

export function getMetrics() {
  return resource(async () => (await apiClient.get<ModelMetrics>('/metrics')).data, () => MOCK_METRICS)
}

export function getModelInfo() {
  return resource(async () => (await apiClient.get<ModelInfo>('/model-info')).data, () => MOCK_MODEL_INFO)
}

export function getMlflowInfo() {
  return resource(async () => (await apiClient.get<MlflowInfo>('/mlflow-info')).data, () => MOCK_MLFLOW_INFO)
}

export function getPipelineStatus() {
  return resource(async () => (await apiClient.get<PipelineStatus>('/pipeline-status')).data, () => MOCK_PIPELINE_STATUS)
}

export function getRecentPredictions() {
  return resource(async () => {
    const response = await apiClient.get<{ items: BackendRecentPrediction[] }>('/recent-predictions')
    return response.data.items.map(mapRecentPrediction)
  }, () => MOCK_RECENT_PREDICTIONS)
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
  const probability = Number(Math.min(0.97, Math.max(0.02, score)).toFixed(4))
  return {
    prediction: probability >= 0.5 ? 'Churn' : 'Not Churn',
    probability, model: 'Demo heuristic', model_version: 'demo-illustration',
    risk_level: getRiskLevel(probability),
  }
}

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'The backend is unreachable. Check the API and try again.'
    const detail = error.response.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join('; ')
  }
  return error instanceof Error ? error.message : 'The request could not be completed.'
}
