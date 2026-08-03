<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useApiList } from '@/composables/useApi'
import { useLocation } from '@/composables/useLocation'
import ResourceCard from '@/components/nearby/ResourceCard.vue'
import type { NearbyResource, NearbyCategory } from '@/types'

const { list: categories } = useApiList<NearbyCategory>('/nearby/categories')
const { list: resources, total, loading, fetch } = useApiList<NearbyResource>('/nearby/resources')
const { updatedAt, refreshing, label: locationLabel, sourceLabel, locate } = useLocation()

// 筛选状态（必须在 watch/函数之前声明，避免 TDZ 访问未初始化变量）
const activeCategory = ref('all')
const sortBy = ref('distance')
const keyword = ref('')
const radius = ref(3)

// 详情弹窗
const showDetail = ref(false)
const selectedResource = ref<NearbyResource | null>(null)

// 有可用位置（配置/旧坐标）即先用它秒出；之后定位刷新到新坐标时 updatedAt 变化再重拉。
// updatedAt 为 null 表示尚未取得任何位置，不拉取（避免空坐标请求）。
watch(updatedAt, (ts) => {
  if (ts) fetchData()
}, { immediate: true })

// 刷新位置：点击后强制重新定位；定位进行中显示 loading；
// 只有真正拿到新位置/坐标才会更新 updatedAt 并触发下方重拉，期间继续用旧坐标。
function refreshLocation() {
  if (refreshing.value) return
  locate(true)
}

function onCategoryChange(catId: string) {
  activeCategory.value = catId
  fetchData()
}

function onSortChange(sort: string) {
  sortBy.value = sort
  fetchData()
}

function onRadiusChange(r: number) {
  radius.value = r
  fetchData()
}

function onSearch() {
  fetchData()
}

function fetchData() {
  fetch({
    category: activeCategory.value,
    keyword: keyword.value,
    sort: sortBy.value,
    radius: radius.value,
  })
}

function openDetail(resource: NearbyResource) {
  selectedResource.value = resource
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
  selectedResource.value = null
}

const sortOptions = [
  { value: 'distance', label: '距离最近' },
  { value: 'rating', label: '评分最高' },
  { value: 'popularity', label: '最受欢迎' },
]

const radiusOptions = [1, 3, 5, 10]

// 数据来源标识（来自后端 POI provider）
const dataSource = computed(() => resources.value[0]?.source || '')
const dataSourceLabel = computed(() => {
  if (dataSource.value === 'amap') return '高德地图'
  if (dataSource.value === 'baidu') return '百度地图'
  return '内置示例数据'
})
</script>

<template>
  <div class="max-w-7xl mx-auto animate-fade-in">
    <!-- 页头 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <span>📍</span> 周边资源
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        发现身边的好去处，美食、购物、医疗、交通一应俱全
      </p>
    </div>

    <!-- 定位状态条 + 刷新位置 -->
    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400 min-w-0">
        <span class="truncate">{{ locationLabel }}</span>
        <span class="px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 whitespace-nowrap">
          {{ sourceLabel }}
        </span>
      </div>
      <button
        @click="refreshLocation"
        :disabled="refreshing"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors whitespace-nowrap disabled:opacity-60"
        title="重新定位后将以新坐标刷新周边"
      >
        <svg
          class="w-3.5 h-3.5"
          :class="refreshing ? 'animate-spin' : ''"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {{ refreshing ? '定位中…' : '刷新位置' }}
      </button>
    </div>

    <!-- 搜索和筛选栏 -->
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <!-- 搜索 -->
      <div class="flex-1 min-w-[200px] relative">
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="keyword"
          @keyup.enter="onSearch"
          type="text"
          placeholder="搜索地点名称、地址..."
          class="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 dark:text-white transition-all"
        />
      </div>

      <!-- 排序 -->
      <div class="flex items-center gap-1.5">
        <span class="text-[10px] text-gray-400">排序:</span>
        <select
          :value="sortBy"
          @change="onSortChange(($event.target as HTMLSelectElement).value)"
          class="text-xs rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary-500/30 cursor-pointer"
        >
          <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>

      <!-- 半径 -->
      <div class="flex items-center gap-1.5">
        <span class="text-[10px] text-gray-400">范围:</span>
        <div class="flex gap-1">
          <button
            v-for="r in radiusOptions"
            :key="r"
            @click="onRadiusChange(r)"
            :class="[
              'px-2.5 py-1.5 text-[10px] font-medium rounded-lg transition-all',
              radius === r
                ? 'bg-primary-500 text-white shadow-sm'
                : 'bg-white dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700 hover:border-primary-300'
            ]"
          >
            {{ r }}km
          </button>
        </div>
      </div>
    </div>

    <!-- 分类标签 -->
    <div class="flex gap-2 mb-6 overflow-x-auto pb-1 scrollbar-hide">
      <button
        v-for="cat in categories"
        :key="cat.id"
        @click="onCategoryChange(cat.id)"
        :class="[
          'flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-200',
          activeCategory === cat.id
            ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
            : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-primary-300'
        ]"
      >
        <span>{{ cat.icon }}</span>
        <span>{{ cat.name }}</span>
      </button>
    </div>

    <!-- 资源网格 -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="i in 6" :key="i" class="card p-5 animate-pulse">
        <div class="flex gap-4 mb-3">
          <div class="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-2xl"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 bg-gray-100 dark:bg-gray-700 rounded-lg w-2/3"></div>
            <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded-lg w-1/2"></div>
          </div>
        </div>
        <div class="space-y-2">
          <div class="h-6 bg-gray-100 dark:bg-gray-700 rounded-lg w-full"></div>
          <div class="h-6 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4"></div>
        </div>
      </div>
    </div>

    <div v-else-if="resources.length === 0" class="text-center py-20">
      <p class="text-5xl mb-4">🗺️</p>
      <p class="text-gray-500 dark:text-gray-400 text-sm">附近暂无相关资源</p>
      <p class="text-gray-400 dark:text-gray-500 text-xs mt-1">试试扩大搜索范围或切换分类</p>
    </div>

    <div v-else>
      <div class="text-xs text-gray-400 mb-4 flex items-center gap-2 flex-wrap">
        <span>
          搜索半径 <span class="font-semibold text-gray-600 dark:text-gray-300">{{ radius }}km</span> 内，
          找到 <span class="font-semibold text-gray-600 dark:text-gray-300">{{ total }}</span> 个资源
        </span>
        <span
          class="px-2 py-0.5 rounded-full text-[10px]"
          :class="dataSource === 'amap' || dataSource === 'baidu'
            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-500'"
        >
          数据来源：{{ dataSourceLabel }}
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ResourceCard
          v-for="resource in resources"
          :key="resource.id"
          :resource="resource"
          @click="openDetail"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showDetail && selectedResource"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
          @click.self="closeDetail"
        >
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-pointer" @click="closeDetail"></div>

          <div class="relative w-full max-w-md max-h-[85vh] overflow-y-auto card animate-slide-up">
            <button
              @click="closeDetail"
              class="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors z-10"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <div class="p-6">
              <!-- 头部 -->
              <div class="flex items-center gap-4 mb-5">
                <span class="text-5xl">{{ selectedResource.icon }}</span>
                <div>
                  <h3 class="text-base font-bold text-gray-900 dark:text-white">{{ selectedResource.name }}</h3>
                  <p class="text-xs text-gray-400 mt-1">{{ selectedResource.address }}</p>
                </div>
              </div>

              <!-- 基本信息网格 -->
              <div class="grid grid-cols-2 gap-3 mb-5">
                <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50">
                  <p class="text-[10px] text-gray-400 mb-1">距离</p>
                  <p class="text-sm font-bold text-primary-600 dark:text-primary-400">
                    {{ selectedResource.distance < 1 ? `${(selectedResource.distance * 1000).toFixed(0)}m` : `${selectedResource.distance.toFixed(1)}km` }}
                  </p>
                </div>
                <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50">
                  <p class="text-[10px] text-gray-400 mb-1">评分</p>
                  <p class="text-sm font-bold text-yellow-500">⭐ {{ selectedResource.rating }}</p>
                </div>
                <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50">
                  <p class="text-[10px] text-gray-400 mb-1">营业时间</p>
                  <p class="text-xs font-medium text-gray-700 dark:text-gray-300">{{ selectedResource.hours }}</p>
                </div>
                <div class="p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50">
                  <p class="text-[10px] text-gray-400 mb-1">状态</p>
                  <span class="badge-success text-[10px]">{{ selectedResource.open_status }}</span>
                </div>
              </div>

              <!-- 标签 -->
              <div class="mb-4">
                <p class="text-[10px] text-gray-400 mb-2">分类标签</p>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="tag in selectedResource.tags"
                    :key="tag"
                    class="text-[10px] px-2.5 py-1 rounded-lg bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>

              <!-- 特色 -->
              <div class="mb-4">
                <p class="text-[10px] text-gray-400 mb-2">特色服务</p>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="feature in selectedResource.features"
                    :key="feature"
                    class="text-[11px] flex items-center gap-1.5 p-2 rounded-lg bg-green-50 dark:bg-green-500/5 text-green-700 dark:text-green-400"
                  >
                    <span>✅</span> {{ feature }}
                  </span>
                </div>
              </div>

              <!-- 电话 -->
              <div v-if="selectedResource.phone" class="pt-4 border-t border-gray-100 dark:border-gray-700">
                <a
                  :href="`tel:${selectedResource.phone}`"
                  class="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors"
                >
                  <span>📞</span> 拨打电话 {{ selectedResource.phone }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-active > .card,
.modal-leave-active > .card {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from > .card {
  transform: scale(0.95) translateY(10px);
}
.modal-leave-to > .card {
  transform: scale(0.95) translateY(10px);
}
</style>
