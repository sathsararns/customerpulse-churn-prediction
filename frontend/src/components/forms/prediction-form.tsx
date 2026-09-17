import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { CreditCard, Loader2, RotateCcw, User, Wifi, Wallet, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { FormSection } from '@/components/forms/form-section'
import { SelectField } from '@/components/forms/select-field'
import { NumberField } from '@/components/forms/number-field'
import {
  defaultPredictionFormValues,
  predictionFormSchema,
  type PredictionFormValues,
} from '@/lib/validators'
import type { PredictionRequest } from '@/types'

const YES_NO = [
  { value: 'Yes', label: 'Yes' },
  { value: 'No', label: 'No' },
] as const

interface PredictionFormProps {
  onSubmit: (payload: PredictionRequest) => void
  submitting: boolean
}

export function PredictionForm({ onSubmit, submitting }: PredictionFormProps) {
  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm<PredictionFormValues>({
    resolver: zodResolver(predictionFormSchema),
    defaultValues: defaultPredictionFormValues,
    mode: 'onBlur',
  })

  const phoneService = watch('PhoneService')
  const internetService = watch('InternetService')
  const hasInternet = internetService !== 'No'

  function submit(values: PredictionFormValues) {
    const payload: PredictionRequest = {
      ...values,
      SeniorCitizen: values.SeniorCitizen === '1' ? 1 : 0,
      tenure: Number(values.tenure),
      MonthlyCharges: Number(values.MonthlyCharges),
      TotalCharges: Number(values.TotalCharges),
    }
    onSubmit(payload)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Customer Profile</CardTitle>
        <CardDescription>
          Enter account details to generate a churn risk prediction from the trained model.
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(submit)} noValidate>
        <CardContent className="space-y-8">
          <FormSection icon={User} title="Personal info">
            <SelectField
              control={control}
              name="gender"
              label="Gender"
              options={[
                { value: 'Female', label: 'Female' },
                { value: 'Male', label: 'Male' },
              ]}
              error={errors.gender?.message}
            />
            <SelectField
              control={control}
              name="SeniorCitizen"
              label="Senior citizen"
              options={[
                { value: '0', label: 'No' },
                { value: '1', label: 'Yes' },
              ]}
              error={errors.SeniorCitizen?.message}
            />
            <SelectField
              control={control}
              name="Partner"
              label="Has partner"
              options={YES_NO}
              error={errors.Partner?.message}
            />
            <SelectField
              control={control}
              name="Dependents"
              label="Has dependents"
              options={YES_NO}
              error={errors.Dependents?.message}
            />
          </FormSection>

          <Separator />

          <FormSection icon={Wallet} title="Account info">
            <NumberField
              register={register}
              name="tenure"
              label="Tenure"
              suffix="months"
              error={errors.tenure?.message}
            />
            <SelectField
              control={control}
              name="Contract"
              label="Contract type"
              options={[
                { value: 'Month-to-month', label: 'Month-to-month' },
                { value: 'One year', label: 'One year' },
                { value: 'Two year', label: 'Two year' },
              ]}
              error={errors.Contract?.message}
            />
            <SelectField
              control={control}
              name="PaperlessBilling"
              label="Paperless billing"
              options={YES_NO}
              error={errors.PaperlessBilling?.message}
            />
            <SelectField
              control={control}
              name="PaymentMethod"
              label="Payment method"
              options={[
                { value: 'Electronic check', label: 'Electronic check' },
                { value: 'Mailed check', label: 'Mailed check' },
                { value: 'Bank transfer (automatic)', label: 'Bank transfer (automatic)' },
                { value: 'Credit card (automatic)', label: 'Credit card (automatic)' },
              ]}
              error={errors.PaymentMethod?.message}
            />
          </FormSection>

          <Separator />

          <FormSection icon={Wifi} title="Service info" description="Line and internet add-ons">
            <SelectField
              control={control}
              name="PhoneService"
              label="Phone service"
              options={YES_NO}
              error={errors.PhoneService?.message}
            />
            <SelectField
              control={control}
              name="MultipleLines"
              label="Multiple lines"
              options={
                phoneService === 'No'
                  ? [{ value: 'No phone service', label: 'No phone service' }]
                  : YES_NO
              }
              error={errors.MultipleLines?.message}
            />
            <SelectField
              control={control}
              name="InternetService"
              label="Internet service"
              options={[
                { value: 'DSL', label: 'DSL' },
                { value: 'Fiber optic', label: 'Fiber optic' },
                { value: 'No', label: 'No internet' },
              ]}
              error={errors.InternetService?.message}
            />
            <SelectField
              control={control}
              name="OnlineSecurity"
              label="Online security"
              options={hasInternet ? YES_NO : [{ value: 'No internet service', label: 'No internet service' }]}
              error={errors.OnlineSecurity?.message}
            />
            <SelectField
              control={control}
              name="OnlineBackup"
              label="Online backup"
              options={hasInternet ? YES_NO : [{ value: 'No internet service', label: 'No internet service' }]}
              error={errors.OnlineBackup?.message}
            />
            <SelectField
              control={control}
              name="DeviceProtection"
              label="Device protection"
              options={hasInternet ? YES_NO : [{ value: 'No internet service', label: 'No internet service' }]}
              error={errors.DeviceProtection?.message}
            />
            <SelectField
              control={control}
              name="TechSupport"
              label="Tech support"
              options={hasInternet ? YES_NO : [{ value: 'No internet service', label: 'No internet service' }]}
              error={errors.TechSupport?.message}
            />
            <SelectField
              control={control}
              name="StreamingTV"
              label="Streaming TV"
              options={hasInternet ? YES_NO : [{ value: 'No internet service', label: 'No internet service' }]}
              error={errors.StreamingTV?.message}
            />
            <SelectField
              control={control}
              name="StreamingMovies"
              label="Streaming movies"
              options={hasInternet ? YES_NO : [{ value: 'No internet service', label: 'No internet service' }]}
              error={errors.StreamingMovies?.message}
              className="sm:col-span-2"
            />
          </FormSection>

          <Separator />

          <FormSection icon={CreditCard} title="Billing info">
            <NumberField
              register={register}
              name="MonthlyCharges"
              label="Monthly charges"
              step="0.01"
              suffix="USD"
              error={errors.MonthlyCharges?.message}
            />
            <NumberField
              register={register}
              name="TotalCharges"
              label="Total charges to date"
              step="0.01"
              suffix="USD"
              error={errors.TotalCharges?.message}
            />
          </FormSection>
        </CardContent>

        <CardFooter className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => reset()}
            disabled={submitting || !isDirty}
            className="w-full sm:w-auto"
          >
            <RotateCcw />
            Reset form
          </Button>
          <Button type="submit" variant="brand" size="lg" disabled={submitting} className="w-full sm:w-auto">
            {submitting ? <Loader2 className="animate-spin" /> : <Zap />}
            {submitting ? 'Running model…' : 'Predict Churn'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
