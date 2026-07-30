import { ref, type Ref } from 'vue'
import type { ApiResponse } from '@/types'

const BASE_URL = '/api'

type ApiUrl = string | (() => string) | Ref<string>

interface UseApiOptions {
  immediate?: boolean
}

function resolveUrl(url: ApiUrl): string {
  if (typeof url === 'string') return url
  if (typeof url === 'function') return url()
  return url.value
}

async function doFetch<T>(fullUrl: string): Promise<ApiResponse<T>> {
  const response = await fetch(fullUrl)

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `HTTP ${response.status}`)
  }

  return response.json()
}

export function useApi<T = any>(url: ApiUrl, options: UseApiOptions = {}) {
  const data: Ref<T | null> = ref(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function execute(params?: Record<string, any>) {
    loading.value = true
    error.value = null

    try {
      let fullUrl = `${BASE_URL}${resolveUrl(url)}`

      if (params) {
        const searchParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            searchParams.append(key, String(value))
          }
        })
        const qs = searchParams.toString()
        if (qs) fullUrl += `?${qs}`
      }

      const json = await doFetch<T>(fullUrl)

      if (json.code === 0) {
        data.value = json.data
      } else {
        error.value = json.message || '请求失败'
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      loading.value = false
    }
  }

  if (options.immediate !== false) {
    execute()
  }

  return { data, loading, error, fetch: execute, refetch: execute }
}

export function useApiList<T = any>(baseUrl: ApiUrl) {
  const list: Ref<T[]> = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function execute(params?: Record<string, any>) {
    loading.value = true
    error.value = null

    try {
      let fullUrl = `${BASE_URL}${resolveUrl(baseUrl)}`

      if (params) {
        const searchParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            searchParams.append(key, String(value))
          }
        })
        const qs = searchParams.toString()
        if (qs) fullUrl += `?${qs}`
      }

      const json = await doFetch<T[]>(fullUrl)

      if (json.code === 0) {
        list.value = json.data || []
        total.value = json.total || 0
      } else {
        error.value = json.message || '请求失败'
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      loading.value = false
    }
  }

  execute()

  return { list, total, loading, error, fetch: execute, refetch: execute }
}
