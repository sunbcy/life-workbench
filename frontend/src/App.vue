<script setup lang="ts">
import Sidebar from '@/components/layout/Sidebar.vue'
import Header from '@/components/layout/Header.vue'
import { useTheme } from '@/composables/useTheme'
import { useSidebar } from '@/composables/useSidebar'

// 初始化主题
useTheme()
const { isOpen: sidebarOpen, close: closeSidebar } = useSidebar()
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
    <!-- 桌面端侧边栏 (md及以上) -->
    <Sidebar class="hidden md:flex" />

    <!-- 移动端侧边栏抽屉 (md以下) -->
    <Teleport to="body">
      <Transition name="drawer">
        <div v-if="sidebarOpen" class="fixed inset-0 z-50 md:hidden">
          <!-- 遮罩 -->
          <div
            class="absolute inset-0 bg-black/40 backdrop-blur-sm"
            @click="closeSidebar"
          ></div>
          <!-- 抽屉 -->
          <div class="absolute left-0 top-0 bottom-0 w-64 animate-slide-in-left">
            <Sidebar class="h-full" />
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden min-w-0">
      <!-- 顶部栏 -->
      <Header />

      <!-- 页面内容 - 响应式内边距 -->
      <main class="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6">
        <router-view v-slot="{ Component, route }">
          <transition
            :name="'page-fade'"
            mode="default"
          >
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style>
/* --- 页面切换动画 --- */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* --- 移动端抽屉动画 --- */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.25s ease;
}
.drawer-enter-active .animate-slide-in-left,
.drawer-leave-active .animate-slide-in-left {
  transition: transform 0.25s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .animate-slide-in-left {
  transform: translateX(-100%);
}
.drawer-leave-to .animate-slide-in-left {
  transform: translateX(-100%);
}

/* 侧边栏滑入关键帧 */
@keyframes slide-in-left {
  from { transform: translateX(-100%); }
  to   { transform: translateX(0); }
}
.animate-slide-in-left {
  animation: slide-in-left 0.25s ease;
}
</style>
