<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'search', keyword: string): void
  (e: 'update:sort', sort: string): void
}>()

const keyword = ref('')
const currentSort = ref('default')

const sortOptions = [
  { value: 'default', label: '默认排序' },
  { value: 'price_asc', label: '价格从低到高' },
  { value: 'price_desc', label: '价格从高到低' },
  { value: 'discount', label: '折扣最大' },
]

function onSearch() {
  emit('search', keyword.value)
}

function onSortChange(sort: string) {
  currentSort.value = sort
  emit('update:sort', sort)
}
</script>

<template>
  <div class="flex items-center gap-3">
    <!-- 搜索框 -->
    <div class="flex-1 relative">
      <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <input
        v-model="keyword"
        @keyup.enter="onSearch"
        type="text"
        placeholder="搜索商品名称..."
        class="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 dark:text-white transition-all"
      />
    </div>

    <!-- 排序 -->
    <div class="flex items-center gap-1.5">
      <span class="text-[10px] text-gray-400 dark:text-gray-500 flex-shrink-0">排序:</span>
      <select
        :value="currentSort"
        @change="onSortChange(($event.target as HTMLSelectElement).value)"
        class="text-xs rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary-500/30 cursor-pointer"
      >
        <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
    </div>
  </div>
</template>
