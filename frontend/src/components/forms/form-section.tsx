import type { LucideIcon } from 'lucide-react'

interface FormSectionProps {
  icon: LucideIcon
  title: string
  description?: string
  children: React.ReactNode
}

export function FormSection({ icon: Icon, title, description, children }: FormSectionProps) {
  return (
    <fieldset className="space-y-4">
      <legend className="mb-1 flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Icon className="h-3.5 w-3.5" />
        </span>
        <span className="text-sm font-semibold">{title}</span>
      </legend>
      {description && <p className="pl-9 text-xs text-muted-foreground">{description}</p>}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  )
}
