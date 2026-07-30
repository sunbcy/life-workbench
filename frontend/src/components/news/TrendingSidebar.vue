<script setup lang="ts">
import { useApi } from '@/composables/useApi'
import type { NewsArticle, HotTag } from '@/types'

const { data: trending, loading } = useApi<{
  trending_articles: NewsArticle[]
  hot_tags: HotTag[]
}>('/news/trending')
</script>

<template>
  <div class="space-y-4">
    <!-- 热门话题 -->
    <div class="card p-5">
      <h3 class="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <span>🔥</span> 热门话题
      </h3>

      <div v-if="loading" class="animate-pulse space-y-2">
        <div v-for="i in 8" :key="i" class="h-6 bg-gray-100 dark:bg-gray-700 rounded-lg"></div>
      </div>

      <div v-else-if="trending && trending.hot_tags?.length" class="flex flex-wrap gap-2">
        <span
          v-for="tag in trending.hot_tags"
          :key="tag.name"
          class="px-3 py-1.5 rounded-xl text-[11px] font-medium cursor-pointer transition-all hover:scale-105"
          :class="tag.count >= 3 ? 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'"
        >
          #{{ tag.name }}
          <span class="text-[9px] opacity-60 ml-1">{{ tag.count }}</span>
        </span>
      </div>
    </div>

    <!-- 热门文章 -->
    <div class="card p-5">
      <h3 class="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <span>📈</span> 今日热榜
      </h3>

      <div v-if="loading" class="animate-pulse space-y-3">
        <div v-for="i in 5" :key="i" class="h-12 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
      </div>

      <div v-else-if="trending && trending.trending_articles?.length" class="space-y-3">
        <div
          v-for="(article, index) in trending.trending_articles"
          :key="article.id"
          class="flex items-start gap-3 p-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer group"
        >
          <span
            :class="index < 3 ? 'bg-gradient-to-br from-red-400 to-orange-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'"
            class="w-5 h-5 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0"
          >
            {{ index + 1 }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-[11px] font-medium text-gray-900 dark:text-white line-clamp-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {{ article.title }}
            </p>
            <p class="text-[9px] text-gray-400 mt-1">{{ article.source }}</p>
          </div>
        </div>
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
