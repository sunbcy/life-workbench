<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed, ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useSidebar } from '@/composables/useSidebar'
import type { ProfileSummary } from '@/types'

const route = useRoute()
const router = useRouter()
const { close: closeSidebar } = useSidebar()

const menuItems = [
  { path: '/', name: 'dashboard', title: '为你推荐', icon: '✨', desc: 'For You' },
  { path: '/price', name: 'price-compare', title: '智能比价', icon: '💰', desc: 'Price Compare' },
  { path: '/nearby', name: 'nearby', title: '周边资源', icon: '📍', desc: 'Nearby' },
  { path: '/news', name: 'news', title: '资讯中心', icon: '📰', desc: 'News' },
  { path: '/profile', name: 'profile', title: '我的画像', icon: '🧬', desc: 'Profile' },
]

const activeMenu = computed(() => route.path)

function navigate(path: string) {
  router.push(path)
  // 移动端：导航后自动关闭侧边栏
  closeSidebar()
}

// 画像状态 — 延迟 2 秒加载，减少首屏并发请求
const { data: profile, fetch: fetchProfile } = useApi<ProfileSummary>('/profile/summary', { immediate: false })
setTimeout(() => fetchProfile(), 2000)
const personalizedEnabled = ref(true)

function togglePersonalization() {
  personalizedEnabled.value = !personalizedEnabled.value
  window.location.reload()
}
</script>

<template>
  <aside class="w-64 md:w-56 h-screen bg-white dark:bg-gray-800 border-r border-gray-100 dark:border-gray-700 flex flex-col flex-shrink-0">
    <!-- Logo 区域 -->
    <div class="h-16 flex items-center justify-between px-5 border-b border-gray-100 dark:border-gray-700">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center text-white text-base shadow-lg shadow-primary-500/25">
          ✨
        </div>
        <div class="min-w-0">
          <h1 class="text-sm font-bold text-gray-900 dark:text-white leading-tight">生活工作台</h1>
          <p class="text-[10px] text-gray-400 dark:text-gray-500 leading-tight">Life Workbench</p>
        </div>
      </div>
      <!-- 移动端关闭按钮 -->
      <button
        @click="closeSidebar"
        class="md:hidden w-7 h-7 flex items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
      <div class="px-3 mb-2">
        <span class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">主菜单</span>
      </div>
      <button
        v-for="item in menuItems"
        :key="item.path"
        @click="navigate(item.path)"
        :class="[
          'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group',
          activeMenu === item.path
            ? 'bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 shadow-sm'
            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50 hover:text-gray-900 dark:hover:text-gray-200'
        ]"
      >
        <span class="text-xl flex-shrink-0">{{ item.icon }}</span>
        <div class="flex-1 text-left">
          <span class="block text-sm">{{ item.title }}</span>
          <span class="block text-[10px] opacity-60">{{ item.desc }}</span>
        </div>
        <div
          v-if="activeMenu === item.path"
          class="w-1.5 h-1.5 rounded-full bg-primary-500"
        ></div>
      </button>

      <!-- 分隔线 -->
      <div class="px-3 pt-4 pb-2">
        <span class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">设置</span>
      </div>

      <!-- 个性化开关 -->
      <div class="px-3 py-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-sm">🧠</span>
            <span class="text-xs font-medium text-gray-600 dark:text-gray-400">个性化推荐</span>
          </div>
          <button
            @click="togglePersonalization"
            :class="[
              'relative w-9 h-5 rounded-full transition-colors duration-200',
              personalizedEnabled ? 'bg-primary-500' : 'bg-gray-300 dark:bg-gray-600'
            ]"
          >
            <span
              :class="[
                'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200',
                personalizedEnabled ? 'translate-x-4' : 'translate-x-0.5'
              ]"
            ></span>
          </button>
        </div>
      </div>
    </nav>

    <!-- 底部信息 -->
    <div class="p-4 border-t border-gray-100 dark:border-gray-700 space-y-2">
      <!-- 画像状态 -->
      <router-link to="/profile" class="flex items-center gap-3 px-2 py-2.5 rounded-xl bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer block">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-sm shadow-sm">
          🧬
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-gray-900 dark:text-white truncate">
            {{ profile ? `${profile.activated_count}/7 维度激活` : '加载中...' }}
          </p>
          <p class="text-[10px] text-gray-400 dark:text-gray-500">我的画像</p>
        </div>
      </router-link>

      <!-- 位置 -->
      <div class="flex items-center gap-3 px-2 py-2.5 rounded-xl bg-gray-50 dark:bg-gray-700/50">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center text-sm shadow-sm">
          📍
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-gray-900 dark:text-white truncate">深圳市 · 南山区</p>
          <p class="text-[10px] text-gray-400 dark:text-gray-500">当前定位</p>
        </div>
      </div>
    </div>
  </aside>
</template>
