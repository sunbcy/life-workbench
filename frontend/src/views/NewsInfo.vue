<script setup lang="ts">
import { ref } from 'vue'
import { useApiList } from '@/composables/useApi'
import ArticleCard from '@/components/news/ArticleCard.vue'
import TrendingSidebar from '@/components/news/TrendingSidebar.vue'
import type { NewsArticle, NewsCategory } from '@/types'

const { list: categories } = useApiList<NewsCategory>('/news/categories')
const { list: articles, total, loading, error: articlesError, fetch } = useApiList<NewsArticle>('/news/articles')

// 筛选状态
const activeCategory = ref('all')
const sortBy = ref('latest')
const keyword = ref('')
const page = ref(1)

// 详情弹窗
const showDetail = ref(false)
const selectedArticle = ref<NewsArticle | null>(null)

function onCategoryChange(catId: string) {
  activeCategory.value = catId
  page.value = 1
  fetchData()
}

function onSortChange(sort: string) {
  sortBy.value = sort
  page.value = 1
  fetchData()
}

function onSearch() {
  page.value = 1
  fetchData()
}

function fetchData() {
  fetch({
    category: activeCategory.value,
    keyword: keyword.value,
    sort: sortBy.value,
    page: page.value,
    page_size: 10,
  })
}

function openDetail(article: NewsArticle) {
  selectedArticle.value = article
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
  selectedArticle.value = null
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
          <button @click="fetchData" class="mt-4 px-4 py-2 rounded-xl text-xs font-medium bg-primary-500 text-white hover:bg-primary-600 transition-colors">
            🔄 重试
          </button>
        </div>

        <div v-else-if="articles.length === 0" class="text-center py-20">
          <p class="text-5xl mb-4">📭</p>
          <p class="text-gray-500 dark:text-gray-400 text-sm">暂无相关资讯</p>
          <p class="text-gray-400 dark:text-gray-500 text-xs mt-1">试试其他分类或关键词</p>
        </div>

        <div v-else class="space-y-4">
          <div class="text-xs text-gray-400 mb-2">
            共 <span class="font-semibold text-gray-600 dark:text-gray-300">{{ total }}</span> 条资讯
          </div>

          <ArticleCard
            v-for="article in articles"
            :key="article.id"
            :article="article"
            @click="openDetail"
          />
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
