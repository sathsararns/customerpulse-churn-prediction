import assert from 'node:assert/strict'
import test from 'node:test'
import { mapRecentPrediction, requestResource, validatePrediction } from '../src/services/api-contract.ts'
import { getRiskLevel } from '../src/lib/risk.ts'
import { predictionFormSchema, defaultPredictionFormValues } from '../src/lib/validators.ts'
import type { PredictionResponse } from '../src/types/index.ts'

test('live failures reject without invoking demo predictions', async () => {
  let demoCalls = 0
  await assert.rejects(requestResource(
    async () => { throw new Error('API unavailable') },
    () => { demoCalls += 1; return 'invented prediction' },
    false,
  ), /API unavailable/)
  assert.equal(demoCalls, 0)
})

test('explicit demo mode never calls the backend', async () => {
  let calls = 0
  const result = await requestResource(async () => { calls += 1; return 'live' }, () => 'demo', true)
  assert.deepEqual(result, { data: 'demo', isLive: false })
  assert.equal(calls, 0)
})

test('live predictions preserve the backend risk and model version', () => {
  const response: PredictionResponse = {
    model: 'classifier', model_version: 'version-a', probability: 0.39,
    prediction: 'Not Churn', risk_level: 'High',
  }
  assert.equal(validatePrediction(response).risk_level, 'High')
  assert.equal(validatePrediction(response).model_version, 'version-a')
})

test('an incomplete API response is rejected rather than estimated', () => {
  assert.throws(() => validatePrediction({
    model: 'classifier', probability: 0.8, prediction: 'Churn',
  } as PredictionResponse), /incomplete prediction/)
})

test('history displays persisted risk and version, including old unversioned rows', () => {
  const item = mapRecentPrediction({
    id: 1, created_at: '2026-10-17T06:00:00Z', model_name: 'classifier',
    model_version: null, prediction: 'Not Churn', probability: 0.65,
    risk_level: 'Low', customer_payload: { gender: 'Female', tenure: 12 },
  })
  assert.equal(item.churnRisk, 'Low')
  assert.equal(item.modelVersion, null)
})

test('demo risk boundaries match the API boundaries', () => {
  for (const [probability, level] of [[0.3999, 'Low'], [0.4, 'Medium'], [0.6999, 'Medium'], [0.7, 'High']] as const) {
    assert.equal(getRiskLevel(probability), level)
  }
})

test('history keeps actual customer and event identifiers', () => {
  const item = mapRecentPrediction({
    id: 5, event_id: 'event-123', customer_id: '00001', source: 'batch',
    created_at: '2026-10-18T06:00:00Z', model_name: 'classifier', model_version: 'v1',
    prediction: 'Not Churn', probability: 0.1, risk_level: 'Low', customer_payload: {},
  })
  assert.equal(item.customerId, '00001')
  assert.equal(item.eventId, 'event-123')
  assert.equal(item.source, 'batch')
})

test('browser validation agrees with backend service relationships', () => {
  assert.equal(predictionFormSchema.safeParse(defaultPredictionFormValues).success, true)
  assert.equal(predictionFormSchema.safeParse({ ...defaultPredictionFormValues, PhoneService: 'No' }).success, false)
  assert.equal(predictionFormSchema.safeParse({ ...defaultPredictionFormValues, InternetService: 'No' }).success, false)
})

test('browser validation rejects fractional tenure and invalid charge ranges', () => {
  for (const overrides of [{ tenure: 1.5 }, { MonthlyCharges: -1 }, { TotalCharges: 50001 }]) {
    assert.equal(predictionFormSchema.safeParse({ ...defaultPredictionFormValues, ...overrides }).success, false)
  }
})
