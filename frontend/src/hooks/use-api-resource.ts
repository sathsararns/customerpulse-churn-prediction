import { useCallback, useEffect, useRef, useState } from 'react'

interface ApiResourceState<T> {
  data: T | null
  isLive: boolean
  loading: boolean
  error: boolean
}

export function useApiResource<T>(fetcher: () => Promise<{ data: T; isLive: boolean }>) {
  const [state, setState] = useState<ApiResourceState<T>>({
    data: null,
    isLive: false,
    loading: true,
    error: false,
  })
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const refetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: false }))
    try {
      const { data, isLive } = await fetcherRef.current()
      setState({ data, isLive, loading: false, error: false })
    } catch {
      setState((s) => ({ ...s, loading: false, error: true }))
    }
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { ...state, refetch }
}
