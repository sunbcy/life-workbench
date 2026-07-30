<script setup lang="ts">
import { useApi } from '@/composables/useApi'
import type { ProfileSummary } from '@/types'

const { data: profile, loading } = useApi<ProfileSummary>('/profile/summary')

// Collect highlights across all active dimensions
function allHighlights(): { text: string; tier: string }[] {
  if (!profile.value) return []
  const items: { text: string; tier: string }[] = []
  for (const dim of profile.value.dimensions) {
    if (dim.active && dim.highlights) {
      for (const h of dim.highlights) {
        items.push({ text: h, tier: dim.tier })
      }
    }
  }
  return items.slice(0, 8)
}

function tierClass(tier: string): string {
  return {
    core: 'bg-primary-50 dark:bg-primary-500/15 text-primary-700 dark:text-primary-300 border-primary-200 dark:border-primary-500/20',
    important: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/20',
    auxiliary: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20',
    reference: 'bg-gray-50 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
  }[tier] || ''
}
</script>

<template>
  <div class="card p-4 mb-6">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <span class="text-sm">🧬</span>
        <h3 class="text-sm font-bold text-gray-900 dark:text-white">你的画像</h3>
        <span v-if="profile" class="text-[10px] text-gray-400">
          {{ profile.activated_count }}/{{ profile.dimensions.length }} 维度激活
        </span>
      </div>
      <router-link to="/profile" class="text-[10px] text-primary-500 hover:underline font-medium">
        查看详情 →
      </router-link>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="flex gap-2 flex-wrap">
      <div v-for="i in 6" :key="i" class="h-7 w-20 rounded-lg bg-gray-100 dark:bg-gray-700 animate-pulse"></div>
    </div>

    <!-- 标签 -->
    <div v-else-if="profile" class="flex gap-1.5 flex-wrap">
      <span
        v-for="(item, idx) in allHighlights()"
        :key="idx"
        :class="tierClass(item.tier)"
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors"
      >
        {{ item.text }}
      </span>
    </div>

    <div v-else class="text-xs text-gray-400">
      未配置画像，请编辑 ~/.life-workbench/profile/ 下的文件
    </div>
  </div>
</template>
