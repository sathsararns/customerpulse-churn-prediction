import { useEffect, useState } from 'react'
import { getHealth } from '@/services/api'

/**
 * Pings GET /health once on mount. Returns `undefined` while checking,
 * `true` once the backend responds, `false` if it's unreachable (mock
 * fallback data is in use). Independent of any single page's data
 * fetch, so the connectivity badge is accurate even before a page's
 * own resource has loaded.
 */
export function useBackendHealth() {
  const [isLive, setIsLive] = useState<boolean | undefined>(undefined)

  useEffect(() => {
    let cancelled = false
    getHealth().then(({ isLive: live }) => {
      if (!cancelled) setIsLive(live)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return isLive
}
