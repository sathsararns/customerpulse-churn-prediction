import { useCallback, useEffect, useRef, useState } from 'react'
import { apiErrorMessage } from '@/services/api'

interface ApiResourceState<T> {
  data: T | null
  isLive: boolean
  loading: boolean
  error: string | null
}

export function useApiResource<T>(
  fetcher: () => Promise<{ data: T; isLive: boolean }>,
  refreshInterval = 0,
) {
  const [state, setState] = useState<ApiResourceState<T>>({
    data: null, isLive: false, loading: true, error: null,
  })
  const sequence = useRef(0)
  const load = useCallback(async () => {
    const request = ++sequence.current
    try {
      const { data, isLive } = await fetcher()
      if (sequence.current === request) setState({ data, isLive, loading: false, error: null })
    } catch (error) {
      if (sequence.current === request) {
        setState({ data: null, isLive: false, loading: false, error: apiErrorMessage(error) })
      }
    }
  }, [fetcher])
  const refetch = useCallback(() => {
    setState((value) => ({ ...value, loading: true }))
    return load()
  }, [load])

  useEffect(() => {
    const initial = window.setTimeout(() => void load(), 0)
    const timer = refreshInterval ? window.setInterval(() => void load(), refreshInterval) : undefined
    return () => {
      window.clearTimeout(initial)
      sequence.current += 1
      if (timer) window.clearInterval(timer)
    }
  }, [load, refreshInterval])

  return { ...state, refetch }
}
