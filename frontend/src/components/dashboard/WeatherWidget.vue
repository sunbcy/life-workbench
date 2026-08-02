<script setup lang="ts">
import { ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { useLocation } from '@/composables/useLocation'
import type { CurrentWeather, ForecastDay, WeatherAlert } from '@/types'

const { data: weather, loading, refetch: refetchWeather } = useApi<CurrentWeather>('/weather/current')
const { data: forecast, refetch: refetchForecast } = useApi<ForecastDay[]>('/weather/forecast')
const { data: alerts, refetch: refetchAlerts } = useApi<WeatherAlert[]>('/weather/alerts')

// 实时定位：设备/网络/IP 上报后，天气应随之刷新
const { label: locationLabel, city, district, updatedAt } = useLocation()

watch(updatedAt, () => {
  refetchWeather()
  refetchForecast()
  refetchAlerts()
})

function weatherIcon(icon: string): string {
  const map: Record<string, string> = {
    'sunny': '☀️',
    'partly-cloudy': '⛅',
    'cloudy': '☁️',
    'rainy': '🌧️',
    'thunderstorm': '⛈️',
    'shower': '🌦️',
    'snow': '🌨️',
  }
  return map[icon] || '🌤️'
}
</script>

<template>
  <div class="card p-5">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <span>🌤️</span> 天气
      </h3>
      <span class="text-[10px] text-gray-400 dark:text-gray-500">
        {{ city ? (district ? `${city}·${district}` : city) : locationLabel }}
      </span>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="animate-pulse space-y-3">
      <div class="h-16 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
      <div class="flex gap-2">
        <div v-for="i in 4" :key="i" class="flex-1 h-16 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
      </div>
    </div>

    <template v-else-if="weather">
      <!-- 当前天气 -->
      <div class="flex items-center justify-between mb-4 p-3 rounded-xl bg-gradient-to-br from-blue-50 to-sky-50 dark:from-blue-500/5 dark:to-sky-500/5">
        <div>
          <div class="flex items-baseline gap-1">
            <span class="text-4xl font-bold text-gray-900 dark:text-white">{{ weather.temperature }}</span>
            <span class="text-sm text-gray-500 dark:text-gray-400">°C</span>
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">体感 {{ weather.feels_like }}°C · {{ weather.condition }}</p>
        </div>
        <span class="text-5xl">{{ weatherIcon(weather.icon) }}</span>
      </div>

      <!-- 天气详情 -->
      <div class="grid grid-cols-3 gap-2 mb-3">
        <div class="text-center p-2 rounded-lg bg-gray-50 dark:bg-gray-700/50">
          <p class="text-[10px] text-gray-400 dark:text-gray-500">湿度</p>
          <p class="text-xs font-semibold text-gray-700 dark:text-gray-300">{{ weather.humidity }}%</p>
        </div>
        <div class="text-center p-2 rounded-lg bg-gray-50 dark:bg-gray-700/50">
          <p class="text-[10px] text-gray-400 dark:text-gray-500">风速</p>
          <p class="text-xs font-semibold text-gray-700 dark:text-gray-300">{{ weather.wind_speed }}km/h</p>
        </div>
        <div class="text-center p-2 rounded-lg bg-gray-50 dark:bg-gray-700/50">
          <p class="text-[10px] text-gray-400 dark:text-gray-500">空气质量</p>
          <p class="text-xs font-semibold text-green-600">{{ weather.aqi_level }}</p>
        </div>
      </div>

      <!-- 预警 -->
      <div v-if="alerts && alerts.length > 0" class="mb-3">
        <div
          v-for="alert in alerts"
          :key="alert.type"
          class="flex items-center gap-2 p-2 rounded-lg bg-yellow-50 dark:bg-yellow-500/5 border border-yellow-100 dark:border-yellow-500/10"
        >
          <span class="text-xs">⚠️</span>
          <span class="text-[10px] text-yellow-700 dark:text-yellow-400 font-medium">{{ alert.message }}</span>
        </div>
      </div>

      <!-- 未来预报 -->
      <div v-if="forecast" class="flex gap-1.5">
        <div
          v-for="day in forecast.slice(0, 5)"
          :key="day.day"
          class="flex-1 text-center p-2 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <p class="text-[10px] text-gray-400 dark:text-gray-500">{{ day.day.slice(0, 2) }}</p>
          <p class="text-sm my-0.5">{{ weatherIcon(day.icon) }}</p>
          <p class="text-[10px] font-semibold text-gray-700 dark:text-gray-300">{{ day.low }}° {{ day.high }}°</p>
        </div>
      </div>
    </template>
  </div>
</template>
