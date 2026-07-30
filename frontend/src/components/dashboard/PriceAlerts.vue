<script setup lang="ts">
import { useApi } from '@/composables/useApi'
import type { PriceAlert } from '@/types'

const { data: alerts, loading } = useApi<PriceAlert[]>('/price/alerts')
</script>

<template>
  <div class="card p-5">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <span>🔔</span> 价格提醒
      </h3>
      <span class="text-[10px] text-primary-500 font-medium cursor-pointer hover:underline">查看全部</span>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="animate-pulse space-y-3">
      <div v-for="i in 3" :key="i" class="h-14 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
    </div>

    <div v-else-if="alerts && alerts.length > 0" class="space-y-2">
      <div
        v-for="alert in alerts"
        :key="alert.id"
        class="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group"
      >
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-gray-900 dark:text-white truncate">{{ alert.product }}</p>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-[10px] text-gray-400 dark:text-gray-500">目标 ¥{{ alert.target_price }}</span>
            <span class="text-[10px] text-gray-300 dark:text-gray-600">|</span>
            <span class="text-[10px] text-orange-500 font-medium">当前最低 ¥{{ alert.current_best }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="badge-info text-[10px]">{{ alert.store }}</span>
          <span class="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse-slow"></span>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-6">
      <p class="text-3xl mb-2">🎉</p>
      <p class="text-xs text-gray-400 dark:text-gray-500">暂无价格提醒</p>
    </div>
  </div>
</template>
