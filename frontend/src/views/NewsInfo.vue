<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useApiList } from '@/composables/useApi'
import { useFeedback } from '@/composables/useFeedback'
import ArticleCard from '@/components/news/ArticleCard.vue'
import TrendingSidebar from '@/components/news/TrendingSidebar.vue'
import type { NewsArticle, NewsCategory, UserNeed, NewsChannel } from '@/types'

const { reportClick, reportDwell, reportOpenLink, reportNotInterested } = useFeedback()

const { list: categories } = useApiList<NewsCategory>('/news/categories')

// 自管文章列表（支持分页累积）
const articles = ref<NewsArticle[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const articlesError = ref<string | null>(null)

// 筛选状态
const activeCategory = ref('all')
const sortBy = ref('latest')
const keyword = ref('')
const page = ref(1)
const pageSize = 10
const hasMore = ref(false)
const sourceFilter = ref('') // 按来源筛选（空=全部）

// 来源筛选可选项（按当前分类从后端 /sources 接口获取，不受分页影响）
// 来源筛选可选项（按国内/国外分组，基于后端 /sources 接口，不受分页影响）
const sourceGroups = ref<{ domestic: string[]; foreign: string[] }>({ domestic: [], foreign: [] })
const sourceOptions = computed(() => [...sourceGroups.value.domestic, ...sourceGroups.value.foreign])

// 视图模式：normal（常规资讯流） / ai（AI 深度推荐）
const viewMode = ref<'normal' | 'ai'>('normal')
// 地理圈层（维度一 & 二）：district(区) / city(市)，仅当地新闻生效
const geoScope = ref<'district' | 'city'>('district')
// AI 推荐：用户诉求 & 推荐列表
const userNeeds = ref<UserNeed[]>([])
const aiLoading = ref(false)
const aiError = ref<string | null>(null)
const aiViewActive = computed(() => viewMode.value === 'ai')

// 当地新闻分类激活时展示「范围层级」切换
const isLocalCategory = computed(() => activeCategory.value === 'local')

// 待接入渠道清单（前端「更多来源」入口，标注 pending；点击弹出待接入说明）
const channels = ref<NewsChannel[]>([])
const showChannelTip = ref<NewsChannel | null>(null)

async function loadChannels() {
  try {
    const resp = await fetch('/api/news/channels')
    const json = await resp.json()
    if (json.code === 0) channels.value = json.data || []
  } catch (e) {
    channels.value = []
  }
}

async function loadAiRecommend() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiError.value = null
  try {
    const resp = await fetch('/api/news/recommend?limit=20&use_llm=true')
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '加载失败')
    articles.value = json.data || []
    userNeeds.value = json.needs || []
    total.value = json.total || articles.value.length
    hasMore.value = false
  } catch (e: any) {
    aiError.value = e?.message || 'AI 推荐加载失败'
  } finally {
    aiLoading.value = false
  }
}

// 切换视图模式：进入 AI 推荐即拉取；返回常规时重置常规列表
function onViewModeChange(mode: 'normal' | 'ai') {
  viewMode.value = mode
  if (mode === 'ai') {
    loadAiRecommend()
  } else {
    resetAndFetch()
  }
}

// 切换地理圈层（区/市）后重新拉取当地新闻
function onGeoScopeChange() {
  if (viewMode.value === 'ai') {
    loadAiRecommend()
  } else {
    resetAndFetch()
  }
}

// 详情弹窗
const showDetail = ref(false)
const selectedArticle = ref<NewsArticle | null>(null)

async function loadSources() {
  try {
    const resp = await fetch(`/api/news/sources?category=${encodeURIComponent(activeCategory.value)}`)
    const json = await resp.json()
    if (json.code === 0 && json.data && !Array.isArray(json.data)) {
      sourceGroups.value = {
        domestic: json.data.domestic || [],
        foreign: json.data.foreign || [],
      }
      // 若当前选中的来源不在新分类的选项中，则清除（避免筛选失效）
      if (sourceFilter.value && !sourceOptions.value.includes(sourceFilter.value)) {
        sourceFilter.value = ''
      }
    }
  } catch (e) {
    // sourceOptions 是 computed，只能通过重置其数据源来清空
    sourceGroups.value = { domestic: [], foreign: [] }
  }
}

function buildParams(p: number) {
  const params: Record<string, string | number> = {
    category: activeCategory.value,
    keyword: keyword.value,
    sort: sortBy.value,
    source: sourceFilter.value,
    page: p,
    page_size: pageSize,
  }
  // 地理圈层仅当地新闻分类生效（维度一 & 二）
  if (activeCategory.value === 'local') {
    params.geo_scope = geoScope.value
  }
  return params
}

// 单飞锁：确保任意时刻只有一个 articles 请求在途，杜绝 page 并发自增
let _inFlight = false

async function loadArticles(reset: boolean) {
  if (_inFlight) return
  _inFlight = true
  if (reset) {
    loading.value = true
  } else {
    loadingMore.value = true
  }
  articlesError.value = null
  try {
    const qs = new URLSearchParams()
    Object.entries(buildParams(page.value)).forEach(([k, v]) => {
      if (v !== '' && v !== undefined && v !== null) qs.append(k, String(v))
    })
    const resp = await fetch(`/api/news/articles?${qs.toString()}`)
    const json = await resp.json()
    if (json.code === 429) {
      // 触发后端限流：停止自动续加载，提示用户手动重试
      hasMore.value = false
      throw new Error(json.message || '请求过于频繁，请稍后再试')
    }
    if (json.code !== 0) throw new Error(json.message || '加载失败')
    const data: NewsArticle[] = json.data || []
    total.value = json.total || 0
    if (reset) {
      articles.value = data
    } else {
      articles.value = articles.value.concat(data)
    }
    // 空页即视为到底（防止 has_more 判断异常导致页码无限自增）
    if (data.length === 0) {
      hasMore.value = false
    } else {
      hasMore.value = json.has_more ?? (articles.value.length < total.value)
    }
  } catch (e: any) {
    articlesError.value = e?.message || '网络错误'
  } finally {
    loading.value = false
    loadingMore.value = false
    _inFlight = false
    // 首屏内容不足一屏时，自动继续加载直到出现滚动条（由 hasMore 自然终止，不递归）
    tryLoadUntilFilled()
  }
}

function resetAndFetch() {
  page.value = 1
  hasMore.value = true
  loadArticles(true)
}

// 前端兜底上限，任何异常逻辑都不应超过此页码（后端硬上限为 MAX_PAGE=100）
const MAX_PAGE = 200
function loadMore() {
  if (_inFlight || loadingMore.value || loading.value || !hasMore.value) return
  if (page.value >= MAX_PAGE) {
    hasMore.value = false
    return
  }
  page.value += 1
  loadArticles(false)
}

// 首屏内容不足一屏（页面无滚动条）时，自动继续加载直到出现滚动条
// 用 nextTick 等待 DOM 更新后判断一次；由 loadArticles 内的 hasMore 自然终止，避免递归风暴
function tryLoadUntilFilled() {
  if (!hasMore.value) return
  if (document.documentElement.scrollHeight <= window.innerHeight + 10) {
    loadMore()
  }
}

function onCategoryChange(catId: string) {
  activeCategory.value = catId
  sourceFilter.value = '' // 切换分类时重置来源筛选
  loadSources()
  resetAndFetch()
}

// 首次加载分类时同步拉取来源列表
function onSortChange(sort: string) {
  sortBy.value = sort
  resetAndFetch()
}

function onSourceChange(src: string) {
  sourceFilter.value = src
  resetAndFetch()
}

function onSearch() {
  resetAndFetch()
}

// 详情打开时刻，用于计算有效停留时长
let detailOpenedAt = 0

function openDetail(article: NewsArticle) {
  selectedArticle.value = article
  showDetail.value = true
  detailOpenedAt = Date.now()
  reportClick(article)
}

function closeDetail() {
  // 关闭前结算停留时长（弱正信号：停留越久越说明感兴趣）
  if (selectedArticle.value && detailOpenedAt) {
    reportDwell(selectedArticle.value, Date.now() - detailOpenedAt)
  }
  detailOpenedAt = 0
  showDetail.value = false
  selectedArticle.value = null
}

// 跳转原文：最强正向信号
function onOpenOriginal(article: NewsArticle) {
  reportOpenLink(article)
}

// 「不感兴趣」：显式负反馈，上报后从当前列表移除，即时给出反馈感
const dismissedIds = ref<Set<string>>(new Set())

function onNotInterested(article: NewsArticle) {
  reportNotInterested(article)
  dismissedIds.value.add(String(article.id))
  dismissedIds.value = new Set(dismissedIds.value)
  articles.value = articles.value.filter(a => String(a.id) !== String(article.id))
  if (total.value > 0) total.value -= 1
  // 若正在详情弹窗中操作，同时关闭弹窗（不重复上报停留）
  if (selectedArticle.value && String(selectedArticle.value.id) === String(article.id)) {
    detailOpenedAt = 0
    showDetail.value = false
    selectedArticle.value = null
  }
}

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

const sortOptions = [
  { value: 'latest', label: '最新发布' },
  { value: 'popular', label: '最多阅读' },
  { value: 'trending', label: '热门优先' },
]

// 无限滚动：列表底部哨兵进入视口时自动加载更多
const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

// 哨兵元素可能在首屏 loading 期间尚未渲染，监听其挂载后再绑定 observer，
// 避免初始化时 sentinel 为 null 导致 observer 失效、滚动到底不加载。
watch(sentinel, (el) => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  if (el) {
    observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) loadMore()
    }, { rootMargin: '200px' })
    observer.observe(el)
  }
})

// 回到顶部按钮
const showToTop = ref(false)
// 记录实际发生滚动的容器（兼容 window 或 App 内 main 等可滚动祖先）
let scrollHost: HTMLElement | Window | null = null

function onScroll() {
  const host = scrollHost
  const top =
    host === window
      ? (host as Window).scrollY
      : (host as HTMLElement)?.scrollTop || 0
  showToTop.value = top > 400
}
function scrollToTop() {
  if (scrollHost === window) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } else if (scrollHost) {
    ;(scrollHost as HTMLElement).scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// capture 阶段捕获任意滚动容器，首次触发时锁定 scrollHost
function onScrollCapture(e: Event) {
  const t = e.target as HTMLElement
  if (t && t !== document && t.scrollHeight > t.clientHeight) {
    scrollHost = t
  } else if (t === document || t === document.documentElement || t === document.body) {
    scrollHost = window
  }
  onScroll()
}

onMounted(() => {
  loadSources()
  loadChannels()
  resetAndFetch()
  document.addEventListener('scroll', onScrollCapture, { passive: true, capture: true })
  onScroll()
})

onBeforeUnmount(() => {
  // 详情弹窗开着就离开页面时，补报一次停留（fetch keepalive 保证能发出）
  if (selectedArticle.value && detailOpenedAt) {
    reportDwell(selectedArticle.value, Date.now() - detailOpenedAt)
    detailOpenedAt = 0
  }
  if (observer) observer.disconnect()
  document.removeEventListener('scroll', onScrollCapture, { capture: true } as EventListenerOptions)
})
</script>

<template>
  <div class="max-w-7xl mx-auto animate-fade-in">
    <!-- 页头 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <span>📰</span> 资讯中心
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        聚合本地资讯、科技动态、财经新闻和生活贴士
      </p>
    </div>

    <div class="flex flex-col lg:flex-row gap-4 lg:gap-6">
      <!-- 主内容 -->
      <div class="flex-1 min-w-0">
        <!-- 搜索和排序 -->
        <div class="flex items-center gap-3 mb-4">
          <div class="flex-1 relative">
            <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              v-model="keyword"
              @keyup.enter="onSearch"
              type="text"
              placeholder="搜索新闻标题、关键词..."
              class="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 dark:text-white transition-all"
            />
          </div>
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
        </div>

        <!-- 视图模式切换：常规资讯流 / AI 深度推荐（维度三） -->
        <div class="flex items-center gap-2 mb-3">
          <button
            @click="onViewModeChange('normal')"
            :class="[
              'px-4 py-1.5 rounded-xl text-xs font-medium transition-all duration-200',
              !aiViewActive
                ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-primary-300'
            ]"
          >
            📰 资讯流
          </button>
          <button
            @click="onViewModeChange('ai')"
            :class="[
              'px-4 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-1.5',
              aiViewActive
                ? 'bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white shadow-lg shadow-violet-500/25'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-violet-300'
            ]"
          >
            🤖 AI 深度推荐
          </button>
        </div>

        <!-- 当地新闻：地理圈层切换（维度一 & 二：区 -> 市） -->
        <div v-if="isLocalCategory && !aiViewActive" class="flex items-center gap-2 mb-3">
          <span class="text-[10px] text-gray-400 shrink-0">范围:</span>
          <button
            @click="geoScope = 'district'; onGeoScopeChange()"
            :class="[
              'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all',
              geoScope === 'district'
                ? 'bg-emerald-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            ]"
          >
            📍 本区（影响优先）
          </button>
          <button
            @click="geoScope = 'city'; onGeoScopeChange()"
            :class="[
              'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all',
              geoScope === 'city'
                ? 'bg-emerald-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            ]"
          >
            🌆 全市（扩大范围）
          </button>
          <span class="text-[10px] text-gray-400 ml-1">按影响范围向你集中</span>
        </div>

        <!-- 分类标签（数量少，换行显示确保全部可见，避免窄屏被横向滚动隐藏） -->
        <div class="flex flex-wrap gap-2 mb-3">
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

        <!-- 来源筛选（按国内 / 国外分组，组内自动换行排列） -->
        <div v-if="sourceOptions.length" class="mb-6 space-y-2">
          <button
            @click="onSourceChange('')"
            :class="[
              'px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all',
              sourceFilter === ''
                ? 'bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            ]"
          >
            全部来源
          </button>

          <div v-if="sourceGroups.domestic.length" class="flex items-center gap-2 flex-wrap">
            <span class="text-[10px] text-gray-400 shrink-0">国内</span>
            <button
              v-for="src in sourceGroups.domestic"
              :key="src"
              @click="onSourceChange(src)"
              :class="[
                'px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all',
                sourceFilter === src
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              {{ src }}
            </button>
          </div>

          <div v-if="sourceGroups.foreign.length" class="flex items-center gap-2 flex-wrap">
            <span class="text-[10px] text-gray-400 shrink-0">国外</span>
            <button
              v-for="src in sourceGroups.foreign"
              :key="src"
              @click="onSourceChange(src)"
              :class="[
                'px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all',
                sourceFilter === src
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              {{ src }}
            </button>
          </div>
        </div>

        <!-- 更多来源（待接入渠道入口，标注 pending；点击弹出说明） -->
        <div v-if="channels.length" class="mb-6">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-[10px] text-gray-400 shrink-0">更多来源(待接入):</span>
            <button
              v-for="ch in channels"
              :key="ch.id"
              @click="showChannelTip = ch"
              :class="[
                'px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all',
                'bg-gray-50 dark:bg-gray-800 text-gray-400 dark:text-gray-500 border border-dashed border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
              ]"
            >
              {{ ch.icon }} {{ ch.name }}
              <span class="ml-1 text-[9px] opacity-70">待接入</span>
            </button>
          </div>
        </div>

        <!-- 待接入渠道说明弹窗 -->
        <div
          v-if="showChannelTip"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          @click.self="showChannelTip = null"
        >
          <div class="card max-w-sm w-full p-5">
            <div class="flex items-center gap-2 mb-3">
              <span class="text-xl">{{ showChannelTip.icon }}</span>
              <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {{ showChannelTip.name }}
              </h3>
              <span class="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-300">
                待接入
              </span>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3">
              {{ showChannelTip.note }}
            </p>
            <p class="text-[11px] text-gray-400 mb-1">接入示例：</p>
            <code class="block text-[11px] bg-gray-100 dark:bg-gray-800 rounded-lg px-2 py-1.5 text-gray-600 dark:text-gray-300 break-all">
              {{ showChannelTip.example }}
            </code>
            <button
              class="mt-4 w-full py-2 rounded-lg bg-primary-500 text-white text-xs font-medium"
              @click="showChannelTip = null"
            >
              知道了
            </button>
          </div>
        </div>


        <!-- AI 深度推荐：加载 / 错误态 -->
        <div v-if="aiViewActive && aiLoading" class="space-y-4">
          <div v-for="i in 5" :key="i" class="card p-5 animate-pulse">
            <div class="flex gap-4">
              <div class="w-14 h-14 bg-gray-100 dark:bg-gray-700 rounded-2xl"></div>
              <div class="flex-1 space-y-2">
                <div class="h-4 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4"></div>
                <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded-lg w-full"></div>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="aiViewActive && aiError" class="card p-8 text-center">
          <p class="text-4xl mb-3">⚠️</p>
          <p class="text-sm text-gray-500 dark:text-gray-400">AI 推荐加载失败</p>
          <p class="text-xs text-gray-400 mt-1">{{ aiError }}</p>
          <button @click="loadAiRecommend" class="mt-4 px-4 py-2 rounded-xl text-xs font-medium bg-violet-500 text-white hover:bg-violet-600 transition-colors">
            🔄 重试
          </button>
        </div>

        <!-- 文章列表 -->
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 5" :key="i" class="card p-5 animate-pulse">
            <div class="flex gap-4">
              <div class="w-14 h-14 bg-gray-100 dark:bg-gray-700 rounded-2xl"></div>
              <div class="flex-1 space-y-2">
                <div class="h-4 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4"></div>
                <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded-lg w-full"></div>
                <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded-lg w-1/2"></div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="articlesError" class="card p-8 text-center">
          <p class="text-4xl mb-3">⚠️</p>
          <p class="text-sm text-gray-500 dark:text-gray-400">资讯加载失败</p>
          <p class="text-xs text-gray-400 mt-1">{{ articlesError }}</p>
          <button @click="resetAndFetch" class="mt-4 px-4 py-2 rounded-xl text-xs font-medium bg-primary-500 text-white hover:bg-primary-600 transition-colors">
            🔄 重试
          </button>
        </div>

        <div v-else-if="articles.length === 0" class="text-center py-20">
          <p class="text-5xl mb-4">📭</p>
          <p class="text-gray-500 dark:text-gray-400 text-sm">暂无相关资讯</p>
          <p class="text-gray-400 dark:text-gray-500 text-xs mt-1">试试其他分类或关键词</p>
        </div>

        <div v-else class="space-y-4">
          <!-- AI 深度推荐：用户诉求画像 -->
          <div v-if="aiViewActive" class="card p-4 mb-1">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-sm font-semibold text-gray-800 dark:text-gray-100">🤖 为你解析的诉求</span>
              <span class="text-[10px] text-violet-500">基于你的画像推断</span>
            </div>
            <div v-if="userNeeds.length" class="flex flex-wrap gap-1.5">
              <span
                v-for="need in userNeeds"
                :key="need.topic"
                class="text-[10px] px-2 py-0.5 rounded-lg bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-500/20"
                :title="need.reason"
              >
                {{ need.category }} · {{ need.topic }}
              </span>
            </div>
            <p v-else class="text-[11px] text-gray-400">尚未配置画像，已按最新资讯展示。去「画像」页打标可获得精准推荐。</p>
          </div>

          <div v-if="!aiViewActive" class="text-xs text-gray-400 mb-2">
            共 <span class="font-semibold text-gray-600 dark:text-gray-300">{{ total }}</span> 条资讯
            <span v-if="sourceFilter" class="ml-1">· 来源：{{ sourceFilter }}</span>
          </div>

          <template v-for="article in articles" :key="article.id">
            <!-- AI 模式：推荐理由条（可解释性） -->
            <div
              v-if="aiViewActive && (article._ai_reason || (article._needs && article._needs.length))"
              class="flex items-start gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-violet-50 to-fuchsia-50 dark:from-violet-500/10 dark:to-fuchsia-500/10 border border-violet-200/60 dark:border-violet-500/20"
            >
              <span class="text-[10px] mt-0.5 shrink-0 px-1.5 py-0.5 rounded bg-violet-500 text-white font-bold">荐</span>
              <div class="min-w-0">
                <p class="text-[11px] text-violet-800 dark:text-violet-200 leading-snug">{{ article._ai_reason }}</p>
                <div v-if="article._needs && article._needs.length" class="flex flex-wrap gap-1 mt-1">
                  <span
                    v-for="n in article._needs"
                    :key="n"
                    class="text-[9px] px-1.5 py-0.5 rounded bg-white/70 dark:bg-gray-800/60 text-violet-700 dark:text-violet-300"
                  >#{{ n }}</span>
                </div>
              </div>
            </div>

            <ArticleCard
              :article="article"
              @click="openDetail"
              @not-interested="onNotInterested"
              @open-link="onOpenOriginal"
            />
          </template>

          <!-- 加载状态提示 -->
          <div v-if="loadingMore" class="pt-2 pb-6 text-center text-xs text-gray-400">
            加载中…
          </div>
          <div v-else-if="!hasMore && articles.length" class="pt-2 pb-6 text-center text-[11px] text-gray-400">
            — 已经到底啦 —
          </div>
          <!-- 无限滚动哨兵：进入视口自动加载更多 -->
          <div ref="sentinel" class="h-1"></div>
        </div>
      </div>

      <!-- 侧边栏 -->
      <div class="w-72 flex-shrink-0 hidden lg:block">
        <TrendingSidebar />
      </div>
    </div>

    <!-- 文章详情弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showDetail && selectedArticle"
          class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4"
          @click.self="closeDetail"
        >
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-pointer" @click="closeDetail"></div>

          <div class="relative w-full max-w-lg max-h-[85vh] overflow-y-auto card animate-slide-up">
            <button
              @click="closeDetail"
              class="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors z-10"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <div class="p-6">
              <!-- 头部图标 -->
              <div class="text-center mb-5">
                <span class="text-6xl">{{ selectedArticle.image }}</span>
              </div>

              <!-- 标题 -->
              <h3 class="text-base font-bold text-gray-900 dark:text-white mb-3">
                <span v-if="selectedArticle.trending" class="inline-flex items-center gap-0.5 mr-1.5 px-1.5 py-0.5 rounded-md bg-red-100 dark:bg-red-500/10 text-[9px] text-red-600 dark:text-red-400 font-bold">
                  🔥 热门
                </span>
                {{ selectedArticle.title }}
              </h3>

              <!-- 元信息 -->
              <div class="flex items-center gap-2 mb-4 text-xs text-gray-400">
                <span class="font-medium text-gray-600 dark:text-gray-400">{{ selectedArticle.source }}</span>
                <span>·</span>
                <span>{{ selectedArticle.author }}</span>
                <span>·</span>
                <span>{{ timeAgo(selectedArticle.published_at) }}</span>
              </div>

              <!-- 摘要/正文 -->
              <div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-700/50 mb-4">
                <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  {{ selectedArticle.summary }}
                </p>
              </div>

              <!-- 标签 -->
              <div class="flex flex-wrap gap-2 mb-4">
                <span
                  v-for="tag in selectedArticle.tags"
                  :key="tag"
                  class="text-[10px] px-2.5 py-1 rounded-lg bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400"
                >
                  #{{ tag }}
                </span>
              </div>

              <!-- 阅读数 -->
              <div class="pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between text-xs text-gray-400">
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  {{ selectedArticle.read_count >= 10000 ? `${(selectedArticle.read_count / 10000).toFixed(1)}万` : selectedArticle.read_count }} 次阅读
                </span>
                <div class="flex items-center gap-2">
                  <button
                    @click="onNotInterested(selectedArticle)"
                    class="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-[11px] font-medium hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-500 transition-colors inline-flex items-center gap-1"
                  >
                    🚫 不感兴趣
                  </button>
                  <a
                    v-if="selectedArticle.link"
                    :href="selectedArticle.link"
                    target="_blank"
                    rel="noopener noreferrer"
                    @click="onOpenOriginal(selectedArticle)"
                    class="px-3 py-1.5 rounded-lg bg-primary-500 text-white text-[11px] font-medium hover:bg-primary-600 transition-colors inline-flex items-center gap-1"
                  >
                    查看原文 ↗
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 回到顶部 -->
    <Transition name="to-top">
      <button
        v-if="showToTop"
        @click="scrollToTop"
        class="fixed bottom-6 right-6 z-40 w-11 h-11 flex items-center justify-center rounded-full bg-primary-500 text-white shadow-lg shadow-primary-500/30 hover:bg-primary-600 hover:scale-105 active:scale-95 transition-all"
        aria-label="回到顶部"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 15l7-7 7 7" />
        </svg>
      </button>
    </Transition>
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

.to-top-enter-active,
.to-top-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.to-top-enter-from,
.to-top-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.9);
}
</style>
