<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  icon: string
  trend?: string
  trendValue?: string
  trendUp?: boolean
  colorClass?: string
}>()
</script>

<template>
  <div class="card p-5 group cursor-pointer">
    <div class="flex items-start justify-between mb-3">
      <div class="flex-1">
        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{ title }}</p>
        <p class="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">{{ value }}</p>
      </div>
      <div
        :class="colorClass || 'bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400'"
        class="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 transition-transform group-hover:scale-110 duration-200"
      >
        {{ icon }}
      </div>
    </div>
    <div v-if="trend" class="flex items-center gap-1.5">
      <span
        :class="trendUp ? 'text-green-500' : 'text-red-500'"
        class="text-xs font-semibold"
      >
        {{ trend }}
      </span>
      <span class="text-[10px] text-gray-400 dark:text-gray-500">{{ trendValue }}</span>
    </div>
  </div>
</template>
