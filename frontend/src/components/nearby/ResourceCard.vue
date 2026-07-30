<script setup lang="ts">
import type { NearbyResource } from '@/types'

defineProps<{
  resource: NearbyResource
}>()

defineEmits<{
  click: [resource: NearbyResource]
}>()

function starColor(rating: number): string {
  if (rating >= 4.5) return 'text-yellow-500'
  if (rating >= 4.0) return 'text-yellow-400'
  if (rating >= 3.0) return 'text-orange-400'
  return 'text-gray-400'
}

function formatDistance(km: number): string {
  if (km < 1) return `${(km * 1000).toFixed(0)}m`
  return `${km.toFixed(1)}km`
}

function formatReviewCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}
</script>

<template>
  <div
    @click="$emit('click', resource)"
    class="card-clickable p-5 group"
  >
    <!-- 头部：图标和基本信息 -->
    <div class="flex items-start gap-4 mb-3">
      <div class="w-12 h-12 rounded-2xl bg-gray-50 dark:bg-gray-700 flex items-center justify-center text-2xl flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
        {{ resource.icon }}
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
          {{ resource.name }}
        </h3>
        <p class="text-[11px] text-gray-400 mt-0.5 truncate">{{ resource.address }}</p>
      </div>
      <!-- 距离标识 -->
      <div class="flex-shrink-0 text-right">
        <p class="text-sm font-bold text-primary-600 dark:text-primary-400">{{ formatDistance(resource.distance) }}</p>
        <p class="text-[9px] text-gray-400">距离</p>
      </div>
    </div>

    <!-- 评分和营业状态 -->
    <div class="flex items-center gap-3 mb-3">
      <div class="flex items-center gap-1">
        <span :class="starColor(resource.rating)" class="text-xs">⭐</span>
        <span class="text-xs font-semibold text-gray-700 dark:text-gray-300">{{ resource.rating }}</span>
        <span class="text-[10px] text-gray-400">({{ formatReviewCount(resource.review_count) }})</span>
      </div>
      <span class="text-gray-300 dark:text-gray-600 text-xs">|</span>
      <span
        :class="resource.open_status.includes('营业') || resource.open_status.includes('开放') || resource.open_status.includes('运营') ? 'badge-success' : 'badge-warning'"
        class="text-[10px]"
      >
        {{ resource.open_status }}
      </span>
      <span class="text-[10px] text-gray-400">{{ resource.hours }}</span>
    </div>

    <!-- 标签 -->
    <div class="flex flex-wrap gap-1.5 mb-3">
      <span
        v-for="tag in resource.tags"
        :key="tag"
        class="text-[10px] px-2 py-0.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
      >
        {{ tag }}
      </span>
    </div>

    <!-- 特色服务 -->
    <div class="flex flex-wrap gap-1.5 pt-3 border-t border-gray-100 dark:border-gray-700">
      <span
        v-for="feature in resource.features.slice(0, 4)"
        :key="feature"
        class="text-[10px] text-primary-500 dark:text-primary-400 flex items-center gap-1"
      >
        <span class="w-1 h-1 rounded-full bg-primary-400"></span>
        {{ feature }}
      </span>
    </div>
  </div>
</template>
