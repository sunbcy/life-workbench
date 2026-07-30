<script setup lang="ts">
import type { NewsArticle } from '@/types'

defineProps<{
  article: NewsArticle
}>()

defineEmits<{
  click: [article: NewsArticle]
}>()

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function formatReadCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}
</script>

<template>
  <div
    @click="$emit('click', article)"
    class="card-clickable p-5 group"
  >
    <div class="flex items-start gap-4">
      <!-- 文章图标 -->
      <div class="w-14 h-14 rounded-2xl bg-gray-50 dark:bg-gray-700 flex items-center justify-center text-3xl flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
        {{ article.image }}
      </div>

      <div class="flex-1 min-w-0">
        <!-- 标题 -->
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-1.5 line-clamp-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
          <span v-if="article.trending" class="inline-flex items-center gap-0.5 mr-1.5 px-1.5 py-0.5 rounded-md bg-red-100 dark:bg-red-500/10 text-[9px] text-red-600 dark:text-red-400 font-bold">
            🔥 热门
          </span>
          {{ article.title }}
        </h3>

        <!-- 摘要 -->
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2 leading-relaxed">
          {{ article.summary }}
        </p>

        <!-- 元信息 -->
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-[10px] font-medium text-gray-600 dark:text-gray-400">{{ article.source }}</span>
          <span class="text-gray-300 dark:text-gray-600 text-[10px]">·</span>
          <span class="text-[10px] text-gray-400">{{ article.author }}</span>
          <span class="text-gray-300 dark:text-gray-600 text-[10px]">·</span>
          <span class="text-[10px] text-gray-400">{{ timeAgo(article.published_at) }}</span>
          <span class="text-gray-300 dark:text-gray-600 text-[10px]">·</span>
          <span class="text-[10px] text-gray-400 flex items-center gap-0.5">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            {{ formatReadCount(article.read_count) }}
          </span>
        </div>

        <!-- 标签 -->
        <div class="flex flex-wrap gap-1.5 mt-2">
          <span
            v-for="tag in article.tags"
            :key="tag"
            class="text-[9px] px-2 py-0.5 rounded-lg bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400"
          >
            #{{ tag }}
          </span>
        </div>
      </div>

      <!-- 右箭头 -->
      <div class="flex-shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity">
        <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
