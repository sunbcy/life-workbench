<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import ProfileBadge from '@/components/feed/ProfileBadge.vue'
import FeedCard from '@/components/feed/FeedCard.vue'
import WeatherWidget from '@/components/dashboard/WeatherWidget.vue'
import QuickActions from '@/components/dashboard/QuickActions.vue'
import type { FeedItem, DashboardStats } from '@/types'

const router = useRouter()

// Mix strategy for feed
const feedMix = ref<'balanced' | 'trending' | 'personal'>('balanced')
const feedSize = ref(10)

// Personalized feed
const feedUrl = computed(() => `/feed/personalized?size=${feedSize.value}&mix=${feedMix.value}`)
const { data: feedItems, loading: feedLoading, fetch: refreshFeed } = useApi<FeedItem[]>(feedUrl)

// Re-fetch when mix strategy or page size changes
watch([feedMix, feedSize], () => {
  refreshFeed()
})

// Stats
const { data: stats } = useApi<DashboardStats>('/dashboard/stats')

// Greeting
function greeting(): string {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
}

function goTo(path: string) {
  router.push(path)
}

function onFeedItemClick(item: FeedItem) {
  // Route to appropriate page based on content type
  if ('source' in item) {
    router.push('/news')
  } else if ('prices' in item || 'lowest_price' in item) {
    router.push('/price')
  } else if ('distance' in item) {
    router.push('/nearby')
  }
}

const mixOptions = [
  { value: 'balanced', label: '⚖️ 均衡', desc: '个人+热度+新鲜' },
  { value: 'personal', label: '👤 个性化', desc: '更偏重你的兴趣' },
  { value: 'trending', label: '🔥 热门', desc: '公众关注的热点' },
] as const
</script>

<template>
  <div class="max-w-7xl mx-auto animate-fade-in">
    <!-- 个性化问候 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
        👋 {{ greeting() }}
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        为你精选了今日内容，基于你的 7 个画像维度智能匹配。
      </p>
    </div>

    <!-- 个人画像状态条 -->
    <ProfileBadge />

    <!-- 快捷操作 + 天气 - 响应式 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4 md:gap-6 mb-4 md:mb-6">
      <div class="md:col-span-2">
        <QuickActions />
      </div>
      <div>
        <WeatherWidget />
      </div>
    </div>

    <!-- 推荐流 -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <span>✨</span> 为你推荐
          <span v-if="stats" class="text-[10px] text-gray-400 font-normal">
            · 今日已省 ¥{{ stats.price_saved_today }}
          </span>
        </h3>

        <!-- 混合策略切换 -->
        <div class="flex items-center gap-1">
          <button
            v-for="opt in mixOptions"
            :key="opt.value"
            @click="feedMix = opt.value"
            :class="[
              'text-[10px] px-2.5 py-1 rounded-lg font-medium transition-all',
              feedMix === opt.value
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            ]"
            :title="opt.desc"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 加载 -->
      <div v-if="feedLoading" class="space-y-3">
        <div v-for="i in 5" :key="i" class="card p-5 animate-pulse">
          <div class="flex gap-3">
            <div class="w-11 h-11 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
            <div class="flex-1 space-y-2">
              <div class="h-4 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4"></div>
              <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded-lg w-1/2"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Feed 列表 -->
      <div v-else-if="feedItems && feedItems.length > 0" class="space-y-3">
        <FeedCard
          v-for="(item, idx) in feedItems"
          :key="`${item.id}-${idx}`"
          :item="item"
          @click="onFeedItemClick"
        />
      </div>

      <!-- 空状态 -->
      <div v-else class="card p-12 text-center">
        <p class="text-4xl mb-3">📭</p>
        <p class="text-sm text-gray-500 dark:text-gray-400">暂无推荐内容</p>
        <p class="text-xs text-gray-400 mt-1">请确保后端已启动且 profile 已配置</p>
      </div>

      <!-- 加载更多 -->
      <div v-if="feedItems && feedItems.length >= feedSize && feedSize < 50" class="text-center mt-4">
        <button
          @click="feedSize += 10"
          class="text-xs text-primary-500 hover:underline font-medium"
        >
          加载更多推荐 ↓
        </button>
      </div>
    </div>
  </div>
</template>
