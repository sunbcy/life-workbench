<script setup lang="ts">
import { ref } from 'vue'
import type { NearbyResource, PlaceVisitInfo } from '@/types'
import { usePlaceVisits } from '@/composables/usePlaceVisits'

const props = defineProps<{
  resource: NearbyResource
}>()

defineEmits<{
  click: [resource: NearbyResource]
}>()

const { postVisit } = usePlaceVisits()

const showExp = ref(false)
const expTaste = ref<'good' | 'bad' | ''>('')
const expNote = ref('')
const saving = ref(false)

function starColor(rating: number): string {
  if (rating >= 4.5) return 'text-yellow-500'
  if (rating >= 4.0) return 'text-yellow-400'
  if (rating >= 3.0) return 'text-orange-400'
  return 'text-gray-400'
}

function formatDistance(km: number): string {
  if (km < 1) return `${(km * 1000).toFixed(0)}m`
  return `${km.toFixed(1)}km`
}

function formatReviewCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}

const visit = () => props.resource.visit_info as PlaceVisitInfo | undefined

// 顶部状态徽标
const statusBadge = () => {
  const v = visit()
  if (!v) return null
  if (v.love_level === 'love') return { icon: '❤️', label: '喜爱', cls: 'bg-rose-100 dark:bg-rose-500/15 text-rose-600 dark:text-rose-400' }
  if (v.love_level === 'like') return { icon: '👍', label: '还行', cls: 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' }
  if (v.love_level === 'dislike') return { icon: '👎', label: '不推荐', cls: 'bg-gray-100 dark:bg-gray-700 text-gray-500' }
  if (v.love_level === 'skip') return { icon: '🚫', label: '暂不考虑', cls: 'bg-gray-100 dark:bg-gray-700 text-gray-400' }
  if (v.visited) return { icon: '✅', label: '来过', cls: 'bg-blue-100 dark:bg-blue-500/15 text-blue-600 dark:text-blue-400' }
  return null
}
const badge = statusBadge()

function stop(e: Event) { e.stopPropagation() }

async function markVisited() {
  await postVisit({ resource_id: props.resource.id, resource_name: props.resource.name, action: 'visited' })
  // 乐观更新（下次 summary 拉取会覆盖为权威值）
  props.resource.visit_info = { ...(props.resource.visit_info || emptyInfo()), ...{ visited: true, visited_at: new Date().toISOString(), not_visited: false, love_level: 'neutral' } } as PlaceVisitInfo
}
async function markNotVisited() {
  await postVisit({ resource_id: props.resource.id, resource_name: props.resource.name, action: 'not_visited' })
  props.resource.visit_info = { ...(props.resource.visit_info || emptyInfo()), ...{ not_visited: true, love_level: 'skip' } } as PlaceVisitInfo
}
function emptyInfo(): PlaceVisitInfo {
  return { visited: false, visited_at: null, not_visited: false, has_good_taste: false, has_bad_taste: false, love_score: 0, love_level: 'neutral', note_count: 0, last_note: '', last_taste: '' }
}

async function saveExperience() {
  if (!expTaste.value) return
  saving.value = true
  await postVisit({ resource_id: props.resource.id, resource_name: props.resource.name, action: 'experience', taste: expTaste.value, note: expNote.value })
  const good = expTaste.value === 'good'
  const prev = props.resource.visit_info || emptyInfo()
  props.resource.visit_info = {
    ...prev,
    visited: true,
    has_good_taste: prev.has_good_taste || good,
    has_bad_taste: prev.has_bad_taste || !good,
    note_count: prev.note_count + 1,
    last_note: expNote.value,
    last_taste: expTaste.value,
    love_level: good ? 'love' : 'dislike',
    love_score: good ? Math.max(prev.love_score, 0.5) : Math.min(prev.love_score, -0.4),
  } as PlaceVisitInfo
  showExp.value = false
  expTaste.value = ''
  expNote.value = ''
  saving.value = false
}
</script>

<template>
  <div
    @click="$emit('click', resource)"
    class="card-clickable p-5 group relative"
  >
    <!-- 顶部状态徽标 -->
    <div v-if="badge" @click="stop" class="absolute top-3 right-3 z-10">
      <span :class="['text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1', badge.cls]">
        <span>{{ badge.icon }}</span>{{ badge.label }}
      </span>
    </div>

    <!-- 头部：图标和基本信息 -->
    <div class="flex items-start gap-4 mb-3">
      <div class="w-12 h-12 rounded-2xl bg-gray-50 dark:bg-gray-700 flex items-center justify-center text-2xl flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
        {{ resource.icon }}
      </div>
      <div class="flex-1 min-w-0 pr-14">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
          {{ resource.name }}
        </h3>
        <p class="text-[11px] text-gray-400 mt-0.5 truncate">{{ resource.address }}</p>
      </div>
      <!-- 距离标识 -->
      <div class="flex-shrink-0 text-right">
        <p class="text-sm font-bold text-primary-600 dark:text-primary-400">{{ formatDistance(resource.distance) }}</p>
        <p class="text-[9px] text-gray-400">距离</p>
      </div>
    </div>

    <!-- 评分和营业状态 -->
    <div class="flex items-center gap-3 mb-3">
      <div class="flex items-center gap-1">
        <span :class="starColor(resource.rating)" class="text-xs">⭐</span>
        <span class="text-xs font-semibold text-gray-700 dark:text-gray-300">{{ resource.rating }}</span>
        <span class="text-[10px] text-gray-400">({{ formatReviewCount(resource.review_count) }})</span>
      </div>
      <span class="text-gray-300 dark:text-gray-600 text-xs">|</span>
      <span
        :class="resource.open_status.includes('营业') || resource.open_status.includes('开放') || resource.open_status.includes('运营') ? 'badge-success' : 'badge-warning'"
        class="text-[10px]"
      >
        {{ resource.open_status }}
      </span>
      <span class="text-[10px] text-gray-400">{{ resource.hours }}</span>
    </div>

    <!-- 标签 -->
    <div class="flex flex-wrap gap-1.5 mb-3">
      <span
        v-for="tag in resource.tags"
        :key="tag"
        class="text-[10px] px-2 py-0.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
      >
        {{ tag }}
      </span>
    </div>

    <!-- 最近体验笔记 -->
    <div v-if="visit()?.last_note" class="mb-3 text-[10px] text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/60 rounded-lg px-2 py-1.5 truncate">
      📝 {{ visit()!.last_taste === 'good' ? '好吃：' : visit()!.last_taste === 'bad' ? '不好吃：' : '' }}{{ visit()!.last_note }}
    </div>

    <!-- 特色服务 -->
    <div class="flex flex-wrap gap-1.5 pt-3 border-t border-gray-100 dark:border-gray-700">
      <span
        v-for="feature in resource.features.slice(0, 4)"
        :key="feature"
        class="text-[10px] text-primary-500 dark:text-primary-400 flex items-center gap-1"
      >
        <span class="w-1 h-1 rounded-full bg-primary-400"></span>
        {{ feature }}
      </span>
    </div>

    <!-- 交互操作条 -->
    <div class="flex items-center gap-1.5 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700" @click="stop">
      <button
        @click="markVisited"
        :class="['text-[10px] px-2 py-1 rounded-lg transition-colors', visit()?.visited ? 'bg-blue-100 dark:bg-blue-500/15 text-blue-600 dark:text-blue-400' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700']"
        title="标记去过"
      >✅ 去过</button>
      <button
        @click="markNotVisited"
        :class="['text-[10px] px-2 py-1 rounded-lg transition-colors', visit()?.not_visited ? 'bg-gray-200 dark:bg-gray-600 text-gray-500' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700']"
        title="标记没去过/不想去"
      >🚫 没去</button>
      <button
        @click="showExp = true"
        class="text-[10px] px-2 py-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="记录体验（好吃/不好吃）"
      >📝 记录</button>
    </div>

    <!-- 体验记录弹层 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showExp" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="showExp = false">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showExp = false"></div>
          <div class="relative w-full max-w-sm card animate-slide-up p-5">
            <h3 class="text-sm font-bold text-gray-900 dark:text-white mb-3">记录「{{ resource.name }}」的体验</h3>
            <div class="flex gap-2 mb-3">
              <button
                @click="expTaste = 'good'"
                :class="['flex-1 py-2 rounded-xl text-sm font-medium transition-all', expTaste === 'good' ? 'bg-rose-100 dark:bg-rose-500/15 text-rose-600 dark:text-rose-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-500']"
              >😋 好吃</button>
              <button
                @click="expTaste = 'bad'"
                :class="['flex-1 py-2 rounded-xl text-sm font-medium transition-all', expTaste === 'bad' ? 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-500']"
              >🤢 不好吃</button>
            </div>
            <textarea
              v-model="expNote"
              rows="2"
              placeholder="补充笔记：比如「牛肉面好吃」「服务差」"
              class="w-full text-xs rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-2.5 focus:outline-none focus:ring-2 focus:ring-primary-500/30 dark:text-white resize-none"
            ></textarea>
            <div class="flex gap-2 mt-3">
              <button @click="showExp = false" class="flex-1 py-2 rounded-xl text-sm text-gray-500 bg-gray-100 dark:bg-gray-700 transition-colors">取消</button>
              <button
                @click="saveExperience"
                :disabled="!expTaste || saving"
                class="flex-1 py-2 rounded-xl text-sm font-medium bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-60"
              >{{ saving ? '保存中…' : '保存' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
