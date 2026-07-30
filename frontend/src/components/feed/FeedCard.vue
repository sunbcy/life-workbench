<script setup lang="ts">
import type { FeedItem } from '@/types'
import RelevanceIndicator from './RelevanceIndicator.vue'

const props = defineProps<{
  item: FeedItem
}>()

const emit = defineEmits<{
  click: [item: FeedItem]
}>()

const categoryColors: Record<string, string> = {
  tech: 'from-blue-500 to-cyan-500',
  local: 'from-emerald-500 to-teal-500',
  finance: 'from-amber-500 to-orange-500',
  life: 'from-pink-500 to-rose-500',
  health: 'from-green-500 to-emerald-500',
  fresh: 'from-lime-500 to-green-500',
  meat: 'from-red-500 to-rose-500',
  grain: 'from-amber-500 to-yellow-500',
  snack: 'from-purple-500 to-pink-500',
  daily: 'from-sky-500 to-blue-500',
  digital: 'from-indigo-500 to-violet-500',
  food: 'from-orange-500 to-red-500',
  market: 'from-blue-500 to-indigo-500',
  hospital: 'from-red-500 to-pink-500',
  bank: 'from-violet-500 to-purple-500',
  education: 'from-teal-500 to-green-500',
  entertainment: 'from-fuchsia-500 to-purple-500',
  service: 'from-gray-500 to-slate-500',
  transport: 'from-cyan-500 to-blue-500',
}

function catColor(cat?: string): string {
  return categoryColors[cat || ''] || 'from-gray-400 to-gray-500'
}

function isNews(item: FeedItem): boolean {
  return 'title' in item && 'source' in item
}

function isProduct(item: FeedItem): boolean {
  return 'prices' in item || 'lowest_price' in item
}

function isNearby(item: FeedItem): boolean {
  return 'distance' in item && 'address' in item
}

function itemType(item: FeedItem): string {
  if (isNews(item)) return '📰'
  if (isProduct(item)) return '💰'
  if (isNearby(item)) return '📍'
  return '📌'
}

function timeAgo(dateStr?: string): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}
</script>

<template>
  <div
    @click="emit('click', item)"
    class="card p-4 cursor-pointer group relative overflow-hidden"
  >
    <!-- 左侧颜色条 -->
    <div
      :class="`bg-gradient-to-b ${catColor(item.category)}`"
      class="absolute left-0 top-0 bottom-0 w-1 rounded-l-2xl opacity-0 group-hover:opacity-100 transition-opacity"
    ></div>

    <div class="flex items-start gap-3">
      <!-- 图标/图片 -->
      <div :class="`bg-gradient-to-br ${catColor(item.category)}`"
        class="w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0 shadow-sm">
        {{ item.image || item.icon || '📌' }}
      </div>

      <!-- 内容 -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-[10px] font-medium text-gray-400 uppercase tracking-wide">
            {{ itemType(item) }}
            {{ isNews(item) ? '资讯' : isProduct(item) ? '比价' : isNearby(item) ? '周边' : '' }}
          </span>
          <span v-if="item.trending" class="text-[9px] bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400 px-1.5 py-0.5 rounded-md font-bold">
            🔥 热门
          </span>
        </div>

        <h4 class="text-sm font-semibold text-gray-900 dark:text-white line-clamp-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
          {{ item.title || item.name }}
        </h4>

        <p v-if="item.summary" class="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
          {{ item.summary }}
        </p>

        <!-- 底部信息栏 -->
        <div class="flex items-center justify-between mt-2.5">
          <div class="flex items-center gap-2 text-[10px] text-gray-400">
            <span v-if="item.source">{{ item.source }}</span>
            <span v-if="item.distance !== undefined">{{ item.distance < 1 ? `${(item.distance * 1000).toFixed(0)}m` : `${item.distance.toFixed(1)}km` }}</span>
            <span v-if="item.lowest_price !== undefined" class="text-primary-600 dark:text-primary-400 font-semibold">¥{{ item.lowest_price }}</span>
            <span v-if="item.rating !== undefined" class="text-yellow-500">⭐ {{ item.rating }}</span>
            <span v-if="item.published_at">{{ timeAgo(item.published_at) }}</span>
          </div>

          <!-- 推荐指示器 -->
          <RelevanceIndicator :recommendation="item._recommendation" />
        </div>
      </div>

      <!-- hover 箭头 -->
      <div class="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-300 dark:text-gray-600">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
