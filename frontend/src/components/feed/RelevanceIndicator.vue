<script setup lang="ts">
import { ref } from 'vue'
import type { Recommendation } from '@/types'

const props = defineProps<{
  recommendation?: Recommendation
}>()

const showTooltip = ref(false)

function scorePct(score: number): string {
  return Math.round(score * 100) + '%'
}

function scoreColor(score: number): string {
  if (score >= 0.7) return 'bg-green-500'
  if (score >= 0.4) return 'bg-primary-500'
  return 'bg-gray-400'
}

function dimLabel(key: string): string {
  const map: Record<string, string> = {
    interests: '兴趣', location: '位置', schedule: '时间',
    preferences: '偏好', health: '健康', social: '社交', budget: '预算',
  }
  return map[key] || key
}
</script>

<template>
  <div v-if="recommendation?.personalized" class="relative inline-flex items-center gap-1">
    <!-- 匹配度圆点 -->
    <div
      @mouseenter="showTooltip = true"
      @mouseleave="showTooltip = false"
      class="flex items-center gap-1.5 px-2 py-0.5 rounded-full cursor-help transition-colors"
      :class="recommendation.composite_score >= 0.5
        ? 'bg-green-50 dark:bg-green-500/10 text-green-700 dark:text-green-400'
        : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'"
    >
      <span :class="scoreColor(recommendation.composite_score)" class="w-1.5 h-1.5 rounded-full inline-block"></span>
      <span class="text-[10px] font-semibold">{{ scorePct(recommendation.composite_score) }} 匹配</span>
    </div>

    <!-- Tooltip -->
    <Transition name="tooltip">
      <div
        v-if="showTooltip && recommendation.match_reasons?.length"
        class="absolute bottom-full left-0 mb-2 w-56 p-3 rounded-xl bg-gray-900 dark:bg-gray-700 text-white text-xs shadow-xl z-50"
      >
        <p class="font-semibold mb-1.5 text-[11px]">为什么推荐？</p>
        <ul class="space-y-1">
          <li v-for="(reason, i) in recommendation.match_reasons" :key="i" class="flex items-start gap-1.5 text-[11px] text-gray-300">
            <span class="text-primary-400 mt-0.5">•</span>
            <span>{{ reason }}</span>
          </li>
        </ul>
        <div class="mt-2 pt-2 border-t border-gray-700 flex gap-3 text-[10px] text-gray-400">
          <span>👤 {{ scorePct(recommendation.relevance_score) }}</span>
          <span>🔥 {{ scorePct(recommendation.trending_score) }}</span>
          <span>🆕 {{ scorePct(recommendation.freshness_score) }}</span>
        </div>
        <!-- 箭头 -->
        <div class="absolute -bottom-1 left-3 w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45"></div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tooltip-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.tooltip-leave-active { transition: opacity 0.1s ease; }
.tooltip-enter-from, .tooltip-leave-to { opacity: 0; transform: translateY(4px); }
</style>
