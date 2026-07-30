<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { useSidebar } from '@/composables/useSidebar'

const route = useRoute()
const { isDark, toggle: toggleTheme } = useTheme()
const { toggle: toggleSidebar } = useSidebar()
const showSearch = ref(false)

const currentTime = ref('')
// 仅在挂载时获取一次时间，避免每秒 setInterval 在移动端造成 CPU 负担
function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', weekday: 'short',
  })
}
updateTime()
</script>

<template>
  <header class="h-16 bg-white/70 dark:bg-gray-800/70 backdrop-blur-xl border-b border-gray-100 dark:border-gray-700 flex items-center justify-between px-3 sm:px-4 md:px-6">
    <!-- 左侧：汉堡菜单 + 页面标题 -->
    <div class="flex items-center gap-2 sm:gap-3 min-w-0">
      <!-- 移动端汉堡菜单按钮 -->
      <button
        @click="toggleSidebar"
        class="md:hidden w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors flex-shrink-0"
        aria-label="菜单"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <div class="flex items-center gap-2 min-w-0">
        <span class="text-base sm:text-lg flex-shrink-0">{{ route.meta.icon }}</span>
        <h2 class="text-base sm:text-lg font-bold text-gray-900 dark:text-white truncate">{{ route.meta.title }}</h2>
      </div>
      <span class="text-gray-300 dark:text-gray-600 hidden sm:inline">|</span>
      <span class="text-[10px] sm:text-xs text-gray-400 dark:text-gray-500 hidden sm:inline truncate">{{ currentTime }}</span>
    </div>

    <!-- 右侧：操作区 -->
    <div class="flex items-center gap-3">
      <!-- 搜索按钮 -->
      <button
        @click="showSearch = !showSearch"
        class="w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        title="搜索"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </button>

      <!-- 通知 -->
      <button
        class="w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors relative"
        title="通知"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <span class="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">3</span>
      </button>

      <!-- 主题切换 -->
      <button
        @click="toggleTheme"
        class="w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
      >
        <!-- 太阳图标 -->
        <svg v-if="isDark" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <!-- 月亮图标 -->
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>

      <!-- 用户头像 -->
      <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white text-sm font-bold shadow-sm shadow-primary-500/25">
        我
      </div>
    </div>

    <!-- 搜索浮层 -->
    <Transition name="fade">
      <div v-if="showSearch" class="absolute top-16 right-6 w-80 card p-3 z-50 animate-slide-up">
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="搜索商品、地点、新闻..."
            class="w-full pl-9 pr-4 py-2 text-sm rounded-xl bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 dark:text-white transition-all"
          />
        </div>
      </div>
    </Transition>
  </header>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
