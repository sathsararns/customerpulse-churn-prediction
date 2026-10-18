import { z } from 'zod'

export const predictionFormSchema = z
  .object({
    customer_id: z.string().trim().max(128, 'Use at most 128 characters').optional(),
    gender: z.enum(['Female', 'Male']),
    SeniorCitizen: z.enum(['0', '1']),
    Partner: z.enum(['Yes', 'No']),
    Dependents: z.enum(['Yes', 'No']),
    tenure: z.coerce
      .number({ message: 'Enter tenure in months' })
      .int('Must be a whole number')
      .min(0, 'Tenure cannot be negative')
      .max(100, 'Tenure looks too high'),
    PhoneService: z.enum(['Yes', 'No']),
    MultipleLines: z.enum(['Yes', 'No', 'No phone service']),
    InternetService: z.enum(['DSL', 'Fiber optic', 'No']),
    OnlineSecurity: z.enum(['Yes', 'No', 'No internet service']),
    OnlineBackup: z.enum(['Yes', 'No', 'No internet service']),
    DeviceProtection: z.enum(['Yes', 'No', 'No internet service']),
    TechSupport: z.enum(['Yes', 'No', 'No internet service']),
    StreamingTV: z.enum(['Yes', 'No', 'No internet service']),
    StreamingMovies: z.enum(['Yes', 'No', 'No internet service']),
    Contract: z.enum(['Month-to-month', 'One year', 'Two year']),
    PaperlessBilling: z.enum(['Yes', 'No']),
    PaymentMethod: z.enum([
      'Electronic check',
      'Mailed check',
      'Bank transfer (automatic)',
      'Credit card (automatic)',
    ]),
    MonthlyCharges: z.coerce
      .number({ message: 'Enter a monthly charge' })
      .min(0, 'Must be positive')
      .max(1000, 'Value looks too high'),
    TotalCharges: z.coerce
      .number({ message: 'Enter total charges to date' })
      .min(0, 'Must be positive')
      .max(50000, 'Value looks too high'),
  })
  .superRefine((data, context) => {
    if ((data.PhoneService === 'No') !== (data.MultipleLines === 'No phone service')) {
      context.addIssue({ code: 'custom', path: ['MultipleLines'], message: 'Multiple lines must match the phone service selection' })
    }
    for (const field of ['OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies'] as const) {
      if ((data.InternetService === 'No') !== (data[field] === 'No internet service')) {
        context.addIssue({ code: 'custom', path: [field], message: 'This option must match the internet service selection' })
      }
    }
  })

export type PredictionFormValues = z.infer<typeof predictionFormSchema>

export const defaultPredictionFormValues: PredictionFormValues = {
  customer_id: '',
  gender: 'Female',
  SeniorCitizen: '0',
  Partner: 'Yes',
  Dependents: 'No',
  tenure: 12,
  PhoneService: 'Yes',
  MultipleLines: 'No',
  InternetService: 'DSL',
  OnlineSecurity: 'Yes',
  OnlineBackup: 'No',
  DeviceProtection: 'Yes',
  TechSupport: 'No',
  StreamingTV: 'Yes',
  StreamingMovies: 'No',
  Contract: 'Month-to-month',
  PaperlessBilling: 'Yes',
  PaymentMethod: 'Electronic check',
  MonthlyCharges: 70.35,
  TotalCharges: 845.2,
}
