<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import Header from '@/components/layout/Header.vue'
import { useTheme } from '@/composables/useTheme'
import { useSidebar } from '@/composables/useSidebar'
import { useLocation } from '@/composables/useLocation'

// 初始化主题
useTheme()
const { isOpen: sidebarOpen, close: closeSidebar } = useSidebar()

// 初始化实时定位（设备 GPS → 网络 IP → 后端默认），并上报后端用于周边/推荐计算
const { init: initLocation } = useLocation()
onMounted(() => { initLocation() })

// 路由切换时的页面级遮罩：点击导航/快捷操作后给出明确的"正在切换"反馈
const router = useRouter()
const navMask = ref(false)
let firstNav = true
let navTimer: ReturnType<typeof setTimeout> | undefined

router.beforeEach(() => {
  if (firstNav) {
    firstNav = false
    return true
  }
  navMask.value = true
  return true
})
router.afterEach(() => {
  // 保持至少 280ms 让遮罩可见，避免瞬间消失看不出反馈
  clearTimeout(navTimer)
  navTimer = setTimeout(() => { navMask.value = false }, 280)
})
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

    <!-- 路由切换遮罩：页面切换时整页轻微模糊+暗化，强化点击反馈 -->
    <Teleport to="body">
      <Transition name="nav-mask">
        <div
          v-if="navMask"
          class="fixed inset-0 z-[60] bg-gray-900/10 backdrop-blur-[1px] pointer-events-none"
        ></div>
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

/* 路由切换遮罩淡入淡出 */
.nav-mask-enter-active,
.nav-mask-leave-active {
  transition: opacity 0.28s ease;
}
.nav-mask-enter-from,
.nav-mask-leave-to {
  opacity: 0;
}
</style>
