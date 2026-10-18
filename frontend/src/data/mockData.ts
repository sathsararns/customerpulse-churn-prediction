import { getRecommendedAction, getRiskLevel } from '@/lib/risk'
import type { HealthStatus, MlflowInfo, ModelInfo, ModelMetrics, PipelineStatus, RecentPrediction } from '@/types'

// Seeded from backend/reports/model_metrics.json and evaluation_report.json
// (the actual trained logistic_regression model), so fallbacks reflect real
// performance rather than placeholder numbers.
export const MOCK_METRICS: ModelMetrics = {
  model_version: 'demo-illustration', prediction_threshold: 0.5,
  accuracy: 0.7970191625266146,
  precision: 0.6375,
  recall: 0.5454545454545454,
  f1_score: 0.5878962536023055,
  roc_auc: 0.8403446226975639,
  confusion_matrix: [
    [919, 116],
    [170, 204],
  ],
  updated_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
}

export const MOCK_MODEL_INFO: ModelInfo = {
  name: 'Logistic Regression — Churn Classifier',
  version: 'demo-illustration', predictionThreshold: 0.5,
  trainingStatus: 'trained',
  lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
  pipelineHealth: 'healthy',
  datasetSize: 7043,
  features: 30,
  algorithm: 'logistic_regression',
}

const NAMES = [
  'Amara Chen',
  'Liam Osei',
  'Priya Ramanathan',
  'Diego Fernandez',
  'Sofia Novak',
  'Ethan Brooks',
  'Mei Tanaka',
  'Noah Whitfield',
  'Isabela Rocha',
  'Kwame Mensah',
  'Elena Petrova',
  'Ravi Deshmukh',
]

export const MOCK_RECENT_PREDICTIONS: RecentPrediction[] = NAMES.map((name, i) => {
  const probability = Number((((i * 37 + 13) % 97) / 100).toFixed(2))
  const risk = getRiskLevel(probability)
  return {
    id: `pred_${1000 + i}`,
    modelVersion: 'demo-illustration',
    customerId: `CUST-${8891 + i * 7}`,
    customerName: name,
    churnRisk: risk,
    probability,
    prediction: probability >= 0.5 ? 'Churn' : 'Not Churn',
    timestamp: new Date(Date.now() - i * 1000 * 60 * 42).toISOString(),
    action: getRecommendedAction(risk),
  }
})

export const MOCK_HEALTH: HealthStatus = {
  status: 'ok', ready: true, model_version: 'demo-illustration',
  selected_model_version: 'demo-illustration', reload_required: false,
  predictionCount: 12, version: 'demo',
}

export const MOCK_MLFLOW_INFO: MlflowInfo = {
  status: 'demo', experiment_name: 'Demo illustration', tracking_uri: 'Demo mode',
  ui_url: 'http://127.0.0.1:8088', checked_at: new Date().toISOString(),
  detail: 'Demo mode: no tracking connection was checked',
}

export const MOCK_PIPELINE_STATUS: PipelineStatus = {
  run: null, serving_model_version: 'demo-illustration', selected_model_version: 'demo-illustration',
}
