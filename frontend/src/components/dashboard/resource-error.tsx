import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ResourceError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="space-y-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
      <p className="flex items-start gap-2"><AlertCircle className="h-4 w-4 shrink-0" />{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>
    </div>
  )
}
