<script setup lang="ts">
import { computed } from 'vue'
import type { PriceProduct, Store } from '@/types'

const props = defineProps<{
  product: PriceProduct
  stores: Store[]
}>()

const emit = defineEmits<{
  click: [product: PriceProduct]
}>()

const storeMap = computed(() => {
  const map: Record<string, Store> = {}
  props.stores.forEach(s => { map[s.id] = s })
  return map
})

const sortedPrices = computed(() => {
  return [...props.product.prices]
    .filter(p => p.in_stock)
    .sort((a, b) => a.price - b.price)
})

const bestPrice = computed(() => sortedPrices.value[0])
const worstPrice = computed(() => sortedPrices.value[sortedPrices.value.length - 1])
const saveAmount = computed(() => {
  if (!bestPrice.value || !worstPrice.value) return 0
  return worstPrice.value.price - bestPrice.value.price
})

const trendColor = computed(() => {
  if (props.product.trend === 'down') return 'text-green-500'
  if (props.product.trend === 'up') return 'text-red-500'
  return 'text-gray-400'
})

const trendIcon = computed(() => {
  if (props.product.trend === 'down') return '↓'
  if (props.product.trend === 'up') return '↑'
  return '→'
})
</script>

<template>
  <div
    @click="emit('click', product)"
    class="card-clickable p-5 group"
  >
    <!-- 顶部：商品信息 -->
    <div class="flex items-start gap-4 mb-4">
      <div class="w-14 h-14 rounded-2xl bg-gray-50 dark:bg-gray-700 flex items-center justify-center text-3xl flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
        {{ product.image }}
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-1 line-clamp-2">
          {{ product.name }}
        </h3>
        <div class="flex items-center gap-2">
          <span class="text-[10px] text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-md">{{ product.unit }}</span>
          <span :class="trendColor" class="text-[11px] font-semibold">
            {{ trendIcon }} {{ Math.abs(product.trend_pct) }}%
          </span>
        </div>
      </div>
      <!-- 最低价展示 -->
      <div class="text-right flex-shrink-0">
        <p class="text-[10px] text-gray-400 mb-0.5">最低价</p>
        <p class="text-xl font-bold text-primary-600 dark:text-primary-400">¥{{ product.lowest_price }}</p>
        <p class="text-[10px] text-gray-400">{{ product.lowest_store }}</p>
      </div>
    </div>

    <!-- 各商家价格条 -->
    <div class="space-y-2">
      <div
        v-for="price in sortedPrices"
        :key="price.store_id"
        class="flex items-center gap-3"
      >
        <!-- 商家名 -->
        <div class="w-16 flex-shrink-0">
          <span class="text-[11px] font-medium text-gray-700 dark:text-gray-300 truncate block">
            {{ storeMap[price.store_id]?.logo }} {{ storeMap[price.store_id]?.name }}
          </span>
        </div>

        <!-- 价格条 -->
        <div class="flex-1 relative h-7 bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
          <!-- 填充条：宽度根据价格比例 -->
          <div
            :class="price.price === bestPrice?.price ? 'bg-gradient-to-r from-primary-400 to-primary-500' : 'bg-gray-200 dark:bg-gray-600'"
            class="absolute inset-y-0 left-0 rounded-lg transition-all duration-500"
            :style="{ width: `${Math.max(30, (bestPrice.price / price.price) * 100)}%` }"
          ></div>
          <!-- 价格文字 -->
          <div class="absolute inset-0 flex items-center justify-between px-3">
            <span
              :class="price.price === bestPrice?.price ? 'text-white' : 'text-gray-500 dark:text-gray-400'"
              class="text-xs font-bold relative z-10"
            >
              ¥{{ price.price }}
            </span>
            <div class="flex items-center gap-1.5 relative z-10">
              <span
                v-if="price.original > price.price"
                class="text-[10px] text-gray-400 line-through"
              >
                ¥{{ price.original }}
              </span>
              <span
                v-if="price.promotion"
                class="text-[9px] bg-red-500 text-white px-1.5 py-0.5 rounded-md font-medium"
              >
                {{ price.promotion }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：省多少 -->
    <div v-if="saveAmount > 0" class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
      <span class="text-[11px] text-gray-500 dark:text-gray-400">
        比最贵省 <span class="text-green-500 font-bold">¥{{ saveAmount.toFixed(1) }}</span>
      </span>
      <span class="text-[10px] text-gray-400">
        共 {{ sortedPrices.length }} 家在售
      </span>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
