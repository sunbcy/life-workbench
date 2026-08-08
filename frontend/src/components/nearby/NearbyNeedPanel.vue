<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { NearbyResource, NeedStateOption, NeedResponse } from '@/types'
import { usePlaceVisits } from '@/composables/usePlaceVisits'
import ResourceCard from '@/components/nearby/ResourceCard.vue'

// ========== 配置：入口形态 ==========
// 折叠多级点选（吃/喝/玩 然后细化）
const TAP_GROUPS: { label: string; icon: string; tags: { tag: string; label: string }[] }[] = [
  { label: '喝', icon: '🥤', tags: [
    { tag: 'water', label: '水' },
    { tag: 'drink', label: '饮品' },
    { tag: 'cafe', label: '咖啡' },
  ] },
  { label: '吃', icon: '🍜', tags: [
    { tag: 'food', label: '食物' },
    { tag: 'snack', label: '零食' },
  ] },
  { label: '玩', icon: '🎡', tags: [
    { tag: 'explore', label: '探索' },
    { tag: 'rest', label: '休息' },
  ] },
  { label: '买', icon: '🛒', tags: [{ tag: 'market', label: '购物' }] },
  { label: '医', icon: '🏥', tags: [{ tag: 'health', label: '医疗' }] },
]

// 隐式状态勾选条（A 路径，轻量、零 token）
const STATE_OPTIONS: NeedStateOption[] = [
  { key: 'hungry', label: '饿' },
  { key: 'thirsty', label: '渴' },
  { key: 'lacking_water', label: '缺水' },
  { key: 'sugar_high', label: '含糖过高' },
  { key: 'tired', label: '疲惫' },
  { key: 'want_explore', label: '想探索' },
]

// ========== 状态 ==========
const text = ref('')
const selectedTags = ref<Set<string>>(new Set())
const states = ref<Record<string, boolean>>({})
const useLLM = ref(false)
const expandedTap = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<NeedResponse | null>(null)
const radius = ref(3)
const radiusOptions = [1, 3, 5, 10]

// 语音输入
const recognizing = ref(false)
let recognition: any = null
const supportsSpeech = computed(() => typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window))

const { fetchSummary, applyVisitInfo } = usePlaceVisits()

function toggleTag(tag: string) {
  if (selectedTags.value.has(tag)) selectedTags.value.delete(tag)
  else selectedTags.value.add(tag)
  selectedTags.value = new Set(selectedTags.value)
}

function toggleState(key: string) {
  states.value[key] = !states.value[key]
  states.value = { ...states.value }
}

function startVoice() {
  if (!supportsSpeech.value) return
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  recognition = new SR()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.onstart = () => { recognizing.value = true }
  recognition.onend = () => { recognizing.value = false }
  recognition.onerror = () => { recognizing.value = false }
  recognition.onresult = (e: any) => {
    text.value = e.results[0][0].transcript
    submit()
  }
  recognition.start()
}

async function submit() {
  if (loading.value) return
  if (!text.value.trim() && selectedTags.value.size === 0) {
    error.value = '请输入需求或点选分类'
    return
  }
  loading.value = true
  error.value = null
  result.value = null
  try {
    const resp = await fetch('/api/nearby/need', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text.value.trim(),
        tapped_tags: [...selectedTags.value],
        use_llm: useLLM.value,
        radius: radius.value,
        personalized: true,
        states: states.value,
      }),
    })
    const json = await resp.json()
    if (json.code === 0) {
      result.value = json as NeedResponse
      // 注入到店自标注信息（来过/好评/喜爱度）
      if (result.value.data.length) {
        fetchSummary(result.value.data).then((summary) => applyVisitInfo(result.value!.data, summary))
      }
    } else {
      error.value = json.message || '检索失败'
    }
  } catch (e: any) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

// 快捷短语
const QUICK_PHRASES = ['我渴了，想喝水', '附近有什么好吃的', '无聊，想出去逛逛', '买点日用品', '有点饿']
function fillPhrase(p: string) { text.value = p; submit() }

const ctxChips = computed(() => {
  if (!result.value) return []
  const c = result.value.context
  const chips: string[] = []
  if (c.time_slot_label) chips.push(`🕐 ${c.time_slot_label}`)
  if (c.location_label) chips.push(`📍 ${c.location_label}`)
  c.user_state_labels.forEach((l) => chips.push(`💡 ${l}`))
  return chips
})

const tagLabels = computed(() => {
  const map = new Map<string, string>()
  TAP_GROUPS.forEach((g) => g.tags.forEach((t) => map.set(t.tag, t.label)))
  return map
})

onMounted(() => {
  // 默认勾选「渴」演示需求中心闭环（用户可随时改）
  states.value = { thirsty: true }
})
</script>

<template>
  <div class="card p-4 mb-6">
    <!-- 标题 -->
    <div class="flex items-center gap-2 mb-3">
      <span class="text-lg">🎯</span>
      <h2 class="text-sm font-bold text-gray-900 dark:text-white">需求中心</h2>
      <span class="text-[10px] text-gray-400">以你的需求为中心，自动带上时间/位置/状态</span>
    </div>

    <!-- 语音 / 文字输入 -->
    <div class="flex gap-2 mb-3">
      <div class="flex-1 relative">
        <input
          v-model="text"
          @keyup.enter="submit"
          type="text"
          placeholder="说点什么：我渴了 / 想吃点东西 / 无聊想逛逛…"
          class="w-full pl-3 pr-10 py-2.5 text-sm rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 dark:text-white transition-all"
        />
        <button
          v-if="supportsSpeech"
          @click="startVoice"
          :disabled="recognizing"
          class="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-primary-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          :title="recognizing ? '聆听中…' : '语音输入'"
        >
          <span :class="recognizing ? 'animate-pulse text-primary-500' : ''">🎤</span>
        </button>
      </div>
      <button
        @click="submit"
        :disabled="loading"
        class="px-4 py-2.5 rounded-xl text-sm font-medium bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-60 whitespace-nowrap"
      >
        {{ loading ? '检索中…' : '找' }}
      </button>
    </div>

    <!-- 折叠多级点选 -->
    <div class="mb-3">
      <button
        @click="expandedTap = !expandedTap"
        class="flex items-center gap-1 text-[11px] text-gray-500 hover:text-primary-500 transition-colors"
      >
        <span>或点选分类</span>
        <span :class="expandedTap ? 'rotate-180' : ''" class="transition-transform">▾</span>
      </button>
      <Transition name="collapse">
        <div v-if="expandedTap" class="mt-2 flex flex-wrap gap-2">
          <div v-for="g in TAP_GROUPS" :key="g.label" class="flex items-center gap-1.5 p-1.5 rounded-xl bg-gray-50 dark:bg-gray-800/60">
            <span class="text-sm">{{ g.icon }}</span>
            <button
              v-for="t in g.tags"
              :key="t.tag"
              @click="toggleTag(t.tag)"
              :class="[
                'px-2.5 py-1 text-[11px] font-medium rounded-lg transition-all',
                selectedTags.has(t.tag)
                  ? 'bg-primary-500 text-white shadow-sm'
                  : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:border-primary-300'
              ]"
            >
              {{ t.label }}
            </button>
          </div>
        </div>
      </Transition>
    </div>

    <!-- 隐式状态勾选条（A 路径，零 token） -->
    <div class="flex flex-wrap items-center gap-1.5 mb-3">
      <span class="text-[10px] text-gray-400 mr-1">当前状态:</span>
      <button
        v-for="opt in STATE_OPTIONS"
        :key="opt.key"
        @click="toggleState(opt.key)"
        :class="[
          'px-2 py-0.5 text-[10px] rounded-full transition-all',
          states[opt.key]
            ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600'
        ]"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- 快捷短语 + C 开关 + 半径 -->
    <div class="flex flex-wrap items-center gap-2 mb-3">
      <button
        v-for="p in QUICK_PHRASES"
        :key="p"
        @click="fillPhrase(p)"
        class="text-[10px] px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-500 hover:text-primary-500 border border-gray-200 dark:border-gray-700 transition-colors"
      >
        {{ p }}
      </button>
      <div class="flex items-center gap-3 ml-auto">
        <label class="flex items-center gap-1 text-[10px] text-gray-500 cursor-pointer" title="启用大模型语义解析（消耗 token）">
          <input type="checkbox" v-model="useLLM" class="accent-primary-500" />
          <span>AI 推断 (C)</span>
        </label>
        <div class="flex items-center gap-1">
          <span class="text-[10px] text-gray-400">范围:</span>
          <button
            v-for="r in radiusOptions"
            :key="r"
            @click="radius = r"
            :class="[
              'px-2 py-0.5 text-[10px] rounded-lg transition-all',
              radius === r
                ? 'bg-primary-500 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700'
            ]"
          >
            {{ r }}km
          </button>
        </div>
      </div>
    </div>

    <!-- 错误 -->
    <p v-if="error" class="text-xs text-red-500 mb-2">{{ error }}</p>

    <!-- 结果上下文 chips -->
    <div v-if="result" class="flex flex-wrap items-center gap-2 mb-3 text-[10px]">
      <span
        v-for="chip in ctxChips"
        :key="chip"
        class="px-2 py-0.5 rounded-full bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400"
      >
        {{ chip }}
      </span>
      <span
        class="px-2 py-0.5 rounded-full"
        :class="result.mode === 'llm-semantic'
          ? 'bg-violet-50 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400'
          : 'bg-gray-100 dark:bg-gray-700 text-gray-500'"
      >
        {{ result.mode === 'llm-semantic' ? 'AI 语义解析' : '本地解析' }}
      </span>
      <span v-if="result.reason" class="text-gray-400">· {{ result.reason }}</span>
    </div>

    <!-- 结果列表 -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="card p-4 animate-pulse">
        <div class="flex gap-3">
          <div class="w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
          <div class="flex-1 space-y-2">
            <div class="h-3 bg-gray-100 dark:bg-gray-700 rounded w-2/3"></div>
            <div class="h-2 bg-gray-100 dark:bg-gray-700 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="result && result.data.length === 0" class="text-center py-10">
      <p class="text-3xl mb-2">🔍</p>
      <p class="text-gray-500 dark:text-gray-400 text-xs">附近没找到匹配的，试试扩大范围或换个说法</p>
    </div>

    <div v-else-if="result" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <ResourceCard
        v-for="resource in result.data"
        :key="resource.id"
        :resource="resource"
        @click="(r: NearbyResource) => $emit('open', r)"
      />
    </div>
  </div>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
.collapse-enter-to,
.collapse-leave-from {
  opacity: 1;
  max-height: 200px;
}
</style>
