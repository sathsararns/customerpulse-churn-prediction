export type YesNo = 'Yes' | 'No'

export interface PredictionRequest {
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
  prediction: 'Churn' | 'Not Churn'
  probability: number
}

export type RiskLevel = 'Low' | 'Medium' | 'High'

export interface ModelMetrics {
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
  trainingStatus: 'trained' | 'training' | 'idle' | 'failed'
  lastUpdated: string
  pipelineHealth: 'healthy' | 'degraded' | 'down'
  datasetSize: number
  features: number
  algorithm: string
}

export interface RecentPrediction {
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
  uptimeSeconds?: number
  version?: string
}

export interface DataSource {
  isLive: boolean
}
