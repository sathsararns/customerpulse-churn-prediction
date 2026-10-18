import { getHealth } from '@/services/api'
import { useApiResource } from '@/hooks/use-api-resource'

export function useBackendHealth() {
  return useApiResource(getHealth, 10000)
}
