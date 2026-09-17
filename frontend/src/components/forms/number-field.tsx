import type { FieldValues, Path, UseFormRegister } from 'react-hook-form'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

interface NumberFieldProps<T extends FieldValues> {
  register: UseFormRegister<T>
  name: Path<T>
  label: string
  error?: string
  step?: string
  suffix?: string
  className?: string
}

export function NumberField<T extends FieldValues>({
  register,
  name,
  label,
  error,
  step = '1',
  suffix,
  className,
}: NumberFieldProps<T>) {
  return (
    <div className={className}>
      <Label htmlFor={name} className="mb-1.5 block">
        {label}
      </Label>
      <div className="relative">
        <Input
          id={name}
          type="number"
          step={step}
          invalid={Boolean(error)}
          aria-invalid={Boolean(error)}
          className={suffix ? 'pr-10' : undefined}
          {...register(name)}
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-muted-foreground">
            {suffix}
          </span>
        )}
      </div>
      {error && <p className="mt-1 text-xs font-medium text-destructive">{error}</p>}
    </div>
  )
}
