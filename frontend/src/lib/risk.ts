import type { RiskLevel } from '@/types'

export function getRiskLevel(probability: number): RiskLevel {
  if (probability >= 0.66) return 'High'
  if (probability >= 0.33) return 'Medium'
  return 'Low'
}

export function getRecommendedAction(risk: RiskLevel): string {
  switch (risk) {
    case 'High':
      return 'Escalate to the retention team and offer a personalized incentive within 24 hours.'
    case 'Medium':
      return 'Send a loyalty offer and schedule a proactive check-in from the account manager.'
    case 'Low':
      return 'No immediate action needed — continue standard engagement and monitor next cycle.'
  }
}
