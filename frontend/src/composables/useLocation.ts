import { ref, computed } from 'vue'

const BASE = '/api'

// 模块级单例状态（侧边栏 / 周边页共享同一份实时位置）
const lat = ref<number | null>(null)
const lng = ref<number | null>(null)
const city = ref('')
const district = ref('')
const source = ref<'device' | 'ip' | 'config' | 'unknown'>('unknown')
const status = ref<'idle' | 'locating' | 'done' | 'error'>('idle')
const refreshing = ref(false)
const error = ref<string | null>(null)
const updatedAt = ref<string | null>(null)
let initialized = false

function reverseGeocode(latVal: number, lngVal: number): Promise<{ city: string; district: string }> {
  // Nominatim 逆地理（OpenStreetMap，免费，无需 key）
  const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latVal}&lon=${lngVal}&accept-language=zh-CN`
  return fetch(url)
    .then((r) => r.json())
    .then((data: any) => {
      const a = data?.address || {}
      return {
        city: a.city || a.town || a.county || a.state || '',
        district: a.suburb || a.city_district || a.county || '',
      }
    })
}

function ipLocate(): Promise<{ lat: number; lng: number; city: string; district: string }> {
  // 网络 IP 定位兜底（免费，无需 key）
  return fetch('https://ipapi.co/json/')
    .then((r) => r.json())
    .then((d: any) => ({
      lat: Number(d.latitude),
      lng: Number(d.longitude),
      city: d.city || '',
      district: d.region || '',
    }))
}

function backendDetect(): Promise<{ lat: number; lng: number; city: string; district: string; source: string }> {
  // 调用后端 /api/location/detect 进行 Android/Termux 原生定位
  return fetch(`${BASE}/location/detect`, { method: 'POST' })
    .then((r) => r.json())
    .then((json: any) => {
      if (json.code === 0 && json.data) {
        const d = json.data
        return {
          lat: Number(d.lat),
          lng: Number(d.lng),
          city: d.city || '',
          district: d.district || '',
          source: d.source || 'backend',
        }
      }
      throw new Error(json.message || '后端定位失败')
    })
}

function pushToBackend() {
  if (lat.value == null || lng.value == null) return
  fetch(`${BASE}/location`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat: lat.value,
      lng: lng.value,
      city: city.value || null,
      district: district.value || null,
      source: source.value,
    }),
  }).catch(() => {})
}

function applyBackendDefault(): Promise<void> {
  return fetch(`${BASE}/location`)
    .then((r) => r.json())
    .then((json: any) => {
      const d = json.data || {}
      lat.value = d.lat
      lng.value = d.lng
      city.value = d.city || ''
      district.value = d.district || ''
      source.value = (d.source as any) || 'config'
      // 拿到可用位置即标记 updatedAt：用已知（配置/旧）位置先秒出，
      // 后续定位刷新成功会再次更新此时间戳触发周边重算。
      if (lat.value != null && lng.value != null) {
        updatedAt.value = new Date().toISOString()
      }
    })
}

function locate(force = false): Promise<void> {
  if (initialized && !force) return Promise.resolve()
  initialized = true
  status.value = 'locating'
  error.value = null
  refreshing.value = true

  const tryDevice = (): Promise<void> =>
    new Promise<void>((resolve, reject) => {
      if (!('geolocation' in navigator)) return reject(new Error('no geolocation'))
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          lat.value = pos.coords.latitude
          lng.value = pos.coords.longitude
          source.value = 'device'
          reverseGeocode(lat.value, lng.value)
            .then((rg) => {
              city.value = rg.city
              district.value = rg.district
            })
            .catch(() => {})
            .finally(() => resolve())
        },
        (err) => reject(err),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 600000 }
      )
    })

  // 调后端用坐标匹配纠正地名（前端 Nominatim 逆地理可能不准）
  // 轻量接口，不走完整定位流水线
  const correctDistrict = (): Promise<void> => {
    if (lat.value == null || lng.value == null) return Promise.resolve()
    return fetch(`${BASE}/location/reverse-geocode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat: lat.value, lng: lng.value }),
    })
      .then((r) => r.json())
      .then((json: any) => {
        if (json.code === 0 && json.data?.city) {
          city.value = json.data.city
          district.value = json.data.district || ''
        }
      })
      .catch(() => {})
  }

  const onLocated = (): Promise<void> => {
    // GPS/IP 拿到坐标后，用后端坐标匹配纠正区名，再推送给后端
    return correctDistrict().then(() => {
      status.value = 'done'
      if (lat.value != null && lng.value != null) {
        updatedAt.value = new Date().toISOString()
      }
      pushToBackend()
    })
  }

  return tryDevice()
    .then(() => onLocated())
    .catch(() => ipLocate().then((ip) => {
      lat.value = ip.lat
      lng.value = ip.lng
      city.value = ip.city
      district.value = ip.district
      source.value = 'ip'
      return onLocated()
    }))
    .catch(() => backendDetect().then((d) => {
      lat.value = d.lat
      lng.value = d.lng
      city.value = d.city
      district.value = d.district
      source.value = 'ip'
      return onLocated()
    }))
    .catch(() => applyBackendDefault().then(() => onLocated()))
    .catch((e: any) => {
      // 定位失败：保留原有位置（不更新 updatedAt），周边继续用旧坐标
      status.value = 'error'
      error.value = e?.message || '定位失败'
    })
    .finally(() => {
      refreshing.value = false
    })
}

function init() {
  // 先取后端默认位置（秒出），再异步尝试实时定位覆盖
  return applyBackendDefault()
    .then(() => locate())
    .catch(() => locate())
}

export function useLocation() {
  const label = computed(() => {
    if (status.value === 'locating') return '定位中…'
    if (city.value) return district.value ? `${city.value} · ${district.value}` : city.value
    if (lat.value != null && lng.value != null) return `${lat.value.toFixed(3)}, ${lng.value.toFixed(3)}`
    return '未知位置'
  })

  const sourceLabel = computed(
    () =>
      ({
        device: '📍 设备定位',
        ip: '🌐 网络定位',
        config: '⚙️ 默认位置',
        unknown: '位置未知',
      }[source.value] || '位置未知')
  )

  return { lat, lng, city, district, source, status, refreshing, error, updatedAt, label, sourceLabel, locate, init }
}
