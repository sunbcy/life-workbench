<script setup lang="ts">
import { computed } from 'vue'
import type { NewsArticle } from '@/types'

const props = defineProps<{
  article: NewsArticle
}>()

defineEmits<{
  click: [article: NewsArticle]
  notInterested: [article: NewsArticle]
  openLink: [article: NewsArticle]
}>()

// 被推荐引擎置顶（Feedly 优先收件箱模式）
const isPinned = computed(() => !!(props.article as any)._pinned)

// 个性化推荐命中（composite_score 较高时标记为「为你推荐」，不打乱时间线顺序）
const isRecommended = computed(() => {
  const rec = (props.article as any)._recommendation
  return !!rec && (rec.composite_score ?? 0) >= 0.5
})

// 推荐理由（可解释性：让用户知道为什么看到这条）
const matchReasons = computed<string[]>(() => {
  const rec = (props.article as any)._recommendation
  return rec?.match_reasons ?? []
})

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
    class="card-clickable p-5 group relative"
    :class="isPinned ? 'ring-1 ring-primary-300 dark:ring-primary-500/40' : ''"
  >
    <!-- 置顶标记（Feedly 优先收件箱） -->
    <span
      v-if="isPinned"
      class="absolute -top-2 left-4 px-2 py-0.5 rounded-md bg-primary-500 text-white text-[9px] font-bold shadow-sm"
    >
      📌 为你精选
    </span>

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
          <span v-else-if="isRecommended" class="inline-flex items-center gap-0.5 mr-1.5 px-1.5 py-0.5 rounded-md bg-primary-50 dark:bg-primary-500/10 text-[9px] text-primary-600 dark:text-primary-400 font-bold">
            ✨ 为你推荐
          </span>
          {{ article.title }}
        </h3>

        <!-- 摘要 -->
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2 leading-relaxed">
          {{ article.summary }}
        </p>

        <!-- 推荐理由（可解释性） -->
        <div v-if="isPinned && matchReasons.length" class="flex flex-wrap gap-1 mb-2">
          <span
            v-for="reason in matchReasons.slice(0, 2)"
            :key="reason"
            class="text-[9px] px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400"
          >
            {{ reason }}
          </span>
        </div>

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
        <div class="flex flex-wrap items-center gap-1.5 mt-2">
          <span
            v-for="tag in article.tags"
            :key="tag"
            class="text-[9px] px-2 py-0.5 rounded-lg bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400"
          >
            #{{ tag }}
          </span>
          <a
            v-if="article.link"
            :href="article.link"
            target="_blank"
            rel="noopener noreferrer"
            @click.stop="$emit('openLink', article)"
            class="text-[9px] px-2 py-0.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors inline-flex items-center gap-0.5"
          >
            原文 ↗
          </a>
        </div>
      </div>

      <!-- 右侧操作区 -->
      <div class="flex-shrink-0 self-center flex items-center gap-1">
        <!-- 不感兴趣：显式负反馈 -->
        <button
          @click.stop="$emit('notInterested', article)"
          title="不感兴趣，减少此类推荐"
          aria-label="不感兴趣"
          class="w-7 h-7 flex items-center justify-center rounded-lg text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-500 transition-all"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <svg class="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
