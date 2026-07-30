import { ref, type Ref } from 'vue'
import type { ApiResponse } from '@/types'

const BASE_URL = '/api'

interface UseApiOptions {
  immediate?: boolean
}

export function useApi<T = any>(url: string | (() => string), options: UseApiOptions = {}) {
  const data: Ref<T | null> = ref(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch(params?: Record<string, any>) {
    loading.value = true
    error.value = null

    try {
      const resolvedUrl = typeof url === 'function' ? url() : url
      let fullUrl = `${BASE_URL}${resolvedUrl}`

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

      const response = await fetch(fullUrl)
      const json: ApiResponse<T> = await response.json()

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
    fetch()
  }

  return { data, loading, error, fetch, refetch: fetch }
}

export function useApiList<T = any>(baseUrl: string | (() => string)) {
  const list: Ref<T[]> = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch(params?: Record<string, any>) {
    loading.value = true
    error.value = null

    try {
      const resolvedUrl = typeof baseUrl === 'function' ? baseUrl() : baseUrl
      let fullUrl = `${BASE_URL}${resolvedUrl}`

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

      const response = await fetch(fullUrl)
      const json = await response.json()

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

  fetch()

  return { list, total, loading, error, fetch, refetch: fetch }
}
