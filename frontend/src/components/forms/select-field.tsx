import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface SelectFieldProps<T extends FieldValues> {
  control: Control<T>
  name: Path<T>
  label: string
  options: readonly { value: string; label: string }[]
  error?: string
  className?: string
}

export function SelectField<T extends FieldValues>({
  control,
  name,
  label,
  options,
  error,
  className,
}: SelectFieldProps<T>) {
  return (
    <div className={className}>
      <Label htmlFor={name} className="mb-1.5 block">
        {label}
      </Label>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger id={name} invalid={Boolean(error)} aria-invalid={Boolean(error)}>
              <SelectValue placeholder={`Select ${label.toLowerCase()}`} />
            </SelectTrigger>
            <SelectContent>
              {options.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />
      {error && <p className="mt-1 text-xs font-medium text-destructive">{error}</p>}
    </div>
  )
}
