<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const actions = [
  { id: 'scan_price', name: '扫码比价', icon: '📷', color: 'from-blue-500 to-cyan-500', bgLight: 'bg-blue-50 dark:bg-blue-500/10', route: '/price' },
  { id: 'nearby', name: '周边探索', icon: '🗺️', color: 'from-green-500 to-emerald-500', bgLight: 'bg-green-50 dark:bg-green-500/10', route: '/nearby' },
  { id: 'news', name: '今日资讯', icon: '📰', color: 'from-purple-500 to-violet-500', bgLight: 'bg-purple-50 dark:bg-purple-500/10', route: '/news' },
  { id: 'weather', name: '天气预报', icon: '🌤️', color: 'from-orange-500 to-amber-500', bgLight: 'bg-orange-50 dark:bg-orange-500/10', route: '/' },
  { id: 'alert', name: '价格提醒', icon: '🔔', color: 'from-red-500 to-rose-500', bgLight: 'bg-red-50 dark:bg-red-500/10', route: '/price' },
  { id: 'favorite', name: '我的收藏', icon: '⭐', color: 'from-yellow-500 to-amber-500', bgLight: 'bg-yellow-50 dark:bg-yellow-500/10', route: '/' },
]

function go(route: string) {
  router.push(route)
}
</script>

<template>
  <div class="card p-5">
    <h3 class="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
      <span>⚡</span> 快捷操作
    </h3>
    <div class="grid grid-cols-3 gap-2.5">
      <button
        v-for="action in actions"
        :key="action.id"
        @click="go(action.route)"
        :class="action.bgLight"
        class="flex flex-col items-center gap-1.5 p-3 rounded-xl hover:scale-105 active:scale-95 transition-all duration-200 group"
      >
        <div :class="`bg-gradient-to-br ${action.color}`" class="w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-sm group-hover:shadow-md transition-shadow">
          {{ action.icon }}
        </div>
        <span class="text-[11px] font-medium text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
          {{ action.name }}
        </span>
      </button>
    </div>
  </div>
</template>
