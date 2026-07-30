<script setup lang="ts">
import { ref, computed } from 'vue'
import { useApiList } from '@/composables/useApi'
import SearchBar from '@/components/price/SearchBar.vue'
import ProductCard from '@/components/price/ProductCard.vue'
import type { PriceProduct, PriceCategory, Store } from '@/types'

// 分类和商家数据
const { list: categories } = useApiList<PriceCategory>('/price/categories')
const { list: stores } = useApiList<Store>('/price/stores')

// 商品列表
const { list: products, total, loading, fetch } = useApiList<PriceProduct>('/price/products')

// 筛选状态
const activeCategory = ref('all')
const sortBy = ref('default')
const keyword = ref('')

// 详情弹窗
const showDetail = ref(false)
const selectedProduct = ref<PriceProduct | null>(null)

function onCategoryChange(catId: string) {
  activeCategory.value = catId
  fetchData()
}

function onSearch(kw: string) {
  keyword.value = kw
  fetchData()
}

function onSortChange(sort: string) {
  sortBy.value = sort
  fetchData()
}

function fetchData() {
  fetch({
    category: activeCategory.value,
    keyword: keyword.value,
    sort: sortBy.value,
  })
}

function openDetail(product: PriceProduct) {
  selectedProduct.value = product
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
  selectedProduct.value = null
}

// 统计数据
const avgSave = computed(() => {
  if (!products.value.length) return 0
  let total = 0
  products.value.forEach(p => {
    const prices = p.prices.filter(pr => pr.in_stock).map(pr => pr.price)
    if (prices.length > 1) {
      total += Math.max(...prices) - Math.min(...prices)
    }
  })
  return (total / products.value.length).toFixed(1)
})
</script>

<template>
  <div class="max-w-7xl mx-auto animate-fade-in">
    <!-- 页头 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <span>💰</span> 智能比价
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        全网比价，帮你找到最优选择。平均每件可省 <span class="text-green-500 font-semibold">¥{{ avgSave }}</span>
      </p>
    </div>

    <!-- 商家列表 -->
    <div class="flex gap-2 mb-4 overflow-x-auto pb-1">
      <div
        v-for="store in stores"
        :key="store.id"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-xs flex-shrink-0"
      >
        <span>{{ store.logo }}</span>
        <span class="text-gray-600 dark:text-gray-400">{{ store.name }}</span>
        <span v-if="store.delivery_fee === 0" class="text-[9px] bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 px-1.5 py-0.5 rounded-md">免配送</span>
      </div>
    </div>

    <!-- 搜索和排序 -->
    <div class="mb-4">
      <SearchBar
        @search="onSearch"
        @update:sort="onSortChange"
      />
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
            : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-700'
        ]"
      >
        <span>{{ cat.icon }}</span>
        <span>{{ cat.name }}</span>
      </button>
    </div>

    <!-- 商品列表 -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 4" :key="i" class="card p-5 animate-pulse">
        <div class="flex gap-4 mb-4">
          <div class="w-14 h-14 bg-gray-100 dark:bg-gray-700 rounded-2xl"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 bg-gray-100 dark:bg-gray-700 rounded-lg w-3/4"></div>
            <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded-lg w-1/4"></div>
          </div>
        </div>
        <div class="space-y-2">
          <div v-for="j in 4" :key="j" class="h-7 bg-gray-100 dark:bg-gray-700 rounded-lg"></div>
        </div>
      </div>
    </div>

    <div v-else-if="products.length === 0" class="text-center py-20">
      <p class="text-5xl mb-4">🔍</p>
      <p class="text-gray-500 dark:text-gray-400 text-sm">没有找到匹配的商品</p>
      <p class="text-gray-400 dark:text-gray-500 text-xs mt-1">试试其他关键词或分类</p>
    </div>

    <div v-else class="space-y-4">
      <div class="text-xs text-gray-400 dark:text-gray-500 mb-2">
        共找到 <span class="font-semibold text-gray-600 dark:text-gray-300">{{ total }}</span> 个商品
      </div>

      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
        :stores="stores"
        @click="openDetail"
      />
    </div>

    <!-- 商品详情弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showDetail && selectedProduct"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
          @click.self="closeDetail"
        >
          <!-- 遮罩 -->
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>

          <!-- 弹窗 -->
          <div class="relative w-full max-w-lg max-h-[85vh] overflow-y-auto card animate-slide-up">
            <!-- 关闭按钮 -->
            <button
              @click="closeDetail"
              class="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors z-10"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <!-- 内容 -->
            <div class="p-6">
              <div class="flex items-center gap-4 mb-5">
                <span class="text-5xl">{{ selectedProduct.image }}</span>
                <div>
                  <h3 class="text-base font-bold text-gray-900 dark:text-white">{{ selectedProduct.name }}</h3>
                  <p class="text-xs text-gray-400 mt-1">{{ selectedProduct.unit }}</p>
                </div>
              </div>

              <!-- 价格对比表 -->
              <div class="space-y-2">
                <div
                  v-for="price in selectedProduct.prices"
                  :key="price.store_id"
                  class="flex items-center justify-between p-3 rounded-xl"
                  :class="price.price === selectedProduct.lowest_price ? 'bg-primary-50 dark:bg-primary-500/5 border border-primary-100 dark:border-primary-500/10' : 'bg-gray-50 dark:bg-gray-700/50'"
                >
                  <div class="flex items-center gap-2">
                    <span
                      v-if="price.price === selectedProduct.lowest_price"
                      class="text-[9px] bg-primary-500 text-white px-1.5 py-0.5 rounded-md font-bold"
                    >
                      最低
                    </span>
                    <span class="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {{ stores.find(s => s.id === price.store_id)?.logo }} {{ stores.find(s => s.id === price.store_id)?.name }}
                    </span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span v-if="!price.in_stock" class="text-[10px] text-red-500">缺货</span>
                    <span v-if="price.promotion" class="text-[9px] text-red-500 bg-red-50 dark:bg-red-500/10 px-1.5 py-0.5 rounded-md">{{ price.promotion }}</span>
                    <div class="text-right">
                      <p class="text-sm font-bold text-gray-900 dark:text-white">¥{{ price.price }}</p>
                      <p v-if="price.original > price.price" class="text-[10px] text-gray-400 line-through">¥{{ price.original }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 统计 -->
              <div class="mt-5 p-4 rounded-xl bg-gray-50 dark:bg-gray-700/50">
                <div class="flex items-center justify-between text-xs">
                  <span class="text-gray-500 dark:text-gray-400">最高价</span>
                  <span class="font-semibold text-gray-700 dark:text-gray-300">
                    ¥{{ Math.max(...selectedProduct.prices.map(p => p.price)) }}
                  </span>
                </div>
                <div class="flex items-center justify-between text-xs mt-2">
                  <span class="text-gray-500 dark:text-gray-400">最低价</span>
                  <span class="font-semibold text-primary-600 dark:text-primary-400">
                    ¥{{ Math.min(...selectedProduct.prices.filter(p => p.in_stock).map(p => p.price)) }}
                  </span>
                </div>
                <div class="flex items-center justify-between text-xs mt-2">
                  <span class="text-gray-500 dark:text-gray-400">可节省</span>
                  <span class="font-semibold text-green-500">
                    ¥{{ (Math.max(...selectedProduct.prices.map(p => p.price)) - Math.min(...selectedProduct.prices.filter(p => p.in_stock).map(p => p.price))).toFixed(1) }}
                  </span>
                </div>
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
