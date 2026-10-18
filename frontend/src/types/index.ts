export type YesNo = 'Yes' | 'No'

export interface PredictionRequest {
  customer_id?: string
  gender: 'Female' | 'Male'
  SeniorCitizen: 0 | 1
  Partner: YesNo
  Dependents: YesNo
  tenure: number
  PhoneService: YesNo
  MultipleLines: YesNo | 'No phone service'
  InternetService: 'DSL' | 'Fiber optic' | 'No'
  OnlineSecurity: YesNo | 'No internet service'
  OnlineBackup: YesNo | 'No internet service'
  DeviceProtection: YesNo | 'No internet service'
  TechSupport: YesNo | 'No internet service'
  StreamingTV: YesNo | 'No internet service'
  StreamingMovies: YesNo | 'No internet service'
  Contract: 'Month-to-month' | 'One year' | 'Two year'
  PaperlessBilling: YesNo
  PaymentMethod:
    | 'Electronic check'
    | 'Mailed check'
    | 'Bank transfer (automatic)'
    | 'Credit card (automatic)'
  MonthlyCharges: number
  TotalCharges: number
}

export interface PredictionResponse {
  event_id?: string
  customer_id?: string | null
  source?: 'api'
  prediction: 'Churn' | 'Not Churn'
  probability: number
  model: string
  model_version: string
  risk_level: RiskLevel
}

export type RiskLevel = 'Low' | 'Medium' | 'High'

export interface ModelMetrics {
  model_version: string
  prediction_threshold: number
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  roc_auc: number
  confusion_matrix: [[number, number], [number, number]]
  updated_at: string
}

export interface ModelInfo {
  name: string
  version: string
  predictionThreshold: number
  trainingStatus: 'trained' | 'training' | 'idle' | 'failed'
  lastUpdated: string
  pipelineHealth: 'healthy' | 'degraded' | 'down'
  datasetSize: number
  features: number
  algorithm: string
}

export interface RecentPrediction {
  eventId?: string
  source?: 'api' | 'batch' | 'stream' | 'legacy'
  modelVersion: string | null
  id: string
  customerId: string
  customerName: string
  churnRisk: RiskLevel
  probability: number
  prediction: 'Churn' | 'Not Churn'
  timestamp: string
  action: string
}

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down'
  ready: boolean
  model_version: string | null
  selected_model_version: string | null
  reload_required: boolean
  predictionCount: number | null
  uptimeSeconds?: number
  version?: string
}

export interface DataSource {
  isLive: boolean
}

export interface MlflowInfo {
  status: 'connected' | 'disconnected' | 'demo'
  experiment_name: string
  tracking_uri: string
  ui_url: string
  checked_at: string
  detail: string | null
  kind?: string
}

export interface PipelineStage {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  started_at: string | null
  completed_at: string | null
  message: string | null
}

export interface PipelineStatus {
  run: {
    run_id: string
    model_version: string
    status: 'running' | 'completed' | 'failed'
    started_at: string
    completed_at: string | null
    error: string | null
    stages: PipelineStage[]
  } | null
  serving_model_version: string | null
  selected_model_version: string | null
}
