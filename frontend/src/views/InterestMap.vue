<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// 当前维度 (从 query 读取, 默认 interests)
const dimension = computed(() => (route.query.dim as string) || 'interests')

// 维度元信息 (与后端 DIMENSION_REGISTRY 对应)
const DIM_META: Record<string, { name: string; icon: string; intro: string; leafHint: string }> = {
  interests: {
    name: '兴趣与技能', icon: '🌳',
    intro: '沿着客观世界的行业/职业分类树不断向下细分，在你感兴趣的节点上打标，引擎会推导你的兴趣路径与末梢。',
    leafHint: '这是最细的叶子节点了。可以在此基础上继续自定义细分。',
  },
  health: {
    name: '健康关注', icon: '🩺',
    intro: '沿着健康知识体系（身体机能 / 营养 / 运动 / 心理 …）下钻，标记你关注或擅长的健康领域，引擎据此推荐相关资讯与周边。',
    leafHint: '这是最细的健康叶子节点了。可以在此基础上继续自定义细分。',
  },
  location: {
    name: '地理关注', icon: '🗺️',
    intro: '沿着城市 → 城区 → 商圈 / 场景下钻，标记你关注或常去的地理区域，让资讯与周边推荐更贴合你的活动范围。',
    leafHint: '这是最细的地理叶子节点了。可以在此基础上继续自定义细分。',
  },
  knowledge: {
    name: '知识体系', icon: '📚',
    intro: '以中美大学本科 — 研究生课程体系为树，从「知识体系」而非职业角度下钻打标，暴露你的认知路径与到达的末梢深度（域 → 学科 → 具体课程）。',
    leafHint: '这是最细的课程叶子节点了。可以在此基础上继续自定义细分。',
  },
}
const meta = computed(() => DIM_META[dimension.value] || DIM_META.interests)

// 标注状态 { nodeId: 'like' | 'skill' | 'know' | ... }
const marks = reactive<Record<string, { like?: boolean; skill?: boolean; know?: boolean; want?: boolean; learning?: boolean; tried?: boolean }>>({})
const customNodes = reactive<Record<string, { name: string; parent_id: string }>>({})
type MarkState = { like?: boolean; skill?: boolean; know?: boolean; want?: boolean; learning?: boolean; tried?: boolean }

const derived = ref<{
  paths: { node_id: string; mark: MarkState; path: { id: string; name: string }[] }[];
  leaves: { id: string; name: string; mark: MarkState }[];
  keywords: string[]; skill_keywords?: string[]; know_keywords?: string[];
  want_keywords?: string[]; learning_keywords?: string[]; tried_keywords?: string[];
  concerns?: string[]; exercises?: string[]; regions?: string[];
  know?: string[]; want?: string[]; learning?: string[]; tried?: string[];
  levels?: Record<string, number>;
}>({ paths: [], leaves: [], keywords: [], skill_keywords: [], know_keywords: [], want_keywords: [], learning_keywords: [], tried_keywords: [], concerns: [], exercises: [], regions: [], know: [], want: [], learning: [], tried: [], levels: {} })

// 下钻路径 (面包屑)
const trail = ref<{ id: string | null; name: string }[]>([{ id: null, name: '客观世界' }])
const currentParent = ref<string | null>(null)
const children = ref<{ id: string; name: string; has_children?: boolean; depth: number; custom?: boolean; external?: boolean }[]>([])
const loading = ref(false)

const showCustomInput = ref(false)
const customName = ref('')
const customError = ref('')

async function loadTree(nodeId: string | null) {
  loading.value = true
  try {
    const dim = dimension.value
    const url = nodeId
      ? `/api/interest-map/tree?dimension=${encodeURIComponent(dim)}&node_id=${encodeURIComponent(nodeId)}`
      : `/api/interest-map/tree?dimension=${encodeURIComponent(dim)}`
    const r = await fetch(url)
    const d = await r.json()
    if (d.code === 0) children.value = d.data
  } finally {
    loading.value = false
  }
}

async function loadMarks() {
  const dim = dimension.value
  const r = await fetch(`/api/interest-map/marks?dimension=${encodeURIComponent(dim)}`)
  const d = await r.json()
  if (d.code === 0) {
    Object.keys(marks).forEach(k => delete marks[k])
    Object.assign(marks, d.data.marks || {})
    Object.keys(customNodes).forEach(k => delete customNodes[k])
    Object.assign(customNodes, d.data.custom_nodes || {})
    derived.value = d.data.derived || { paths: [], leaves: [], keywords: [], skill_keywords: [], concerns: [], exercises: [], regions: [] }
  }
}

function isMarked(id: string): { like: boolean; skill: boolean; know: boolean; want: boolean; learning: boolean; tried: boolean } {
  // marks[id] 为 {like?, skill?, know?, want?, learning?, tried?} 集合; 兼容旧字符串格式
  const v = marks[id] as any
  if (typeof v === 'string') return { like: v === 'like', skill: v === 'skill', know: false, want: false, learning: false, tried: false }
  return { like: !!v?.like, skill: !!v?.skill, know: !!v?.know, want: !!v?.want, learning: !!v?.learning, tried: !!v?.tried }
}

async function toggleMark(id: string, mark: 'like' | 'skill' | 'know' | 'want' | 'learning' | 'tried') {
  try {
    const r = await fetch('/api/interest-map/tag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dimension: dimension.value, node_id: id, mark }),
    })
    const d = await r.json()
    if (d.code === 0) {
      Object.keys(marks).forEach(k => delete marks[k])
      Object.assign(marks, d.data.marks || {})
      derived.value = d.data.derived || derived.value
    }
  } catch (e) {
    // 失败保持乐观更新前的状态 (marks 已被后端返回覆盖)
  }
}

function drill(id: string, name: string) {
  trail.value.push({ id, name })
  currentParent.value = id
  loadTree(id)
}

function goTrail(index: number) {
  trail.value = trail.value.slice(0, index + 1)
  currentParent.value = trail.value[index].id
  loadTree(currentParent.value)
}

async function addCustom() {
  customError.value = ''
  const name = customName.value.trim()
  if (!name) { customError.value = '名称不能为空'; return }
  if (!currentParent.value) { customError.value = '请先选择一个分类再添加'; return }
  try {
    const r = await fetch('/api/interest-map/custom-node', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dimension: dimension.value, parent_id: currentParent.value, name }),
    })
    const d = await r.json()
    if (d.code === 0) {
      customNodes[d.data.id] = { name: d.data.name, parent_id: currentParent.value! }
      customName.value = ''
      showCustomInput.value = false
      await loadTree(currentParent.value)
    } else {
      customError.value = d.message || '添加失败'
    }
  } catch (e: any) {
    customError.value = e.message
  }
}

// 一键导出全部维度 (YAML) 到本地
function exportAll() {
  const a = document.createElement('a')
  a.href = '/api/interest-map/export'
  a.download = 'life-workbench-profile.yaml'
  document.body.appendChild(a)
  a.click()
  a.remove()
}

// AI 职业导师报告
const mentorReport = ref('')
const mentorLoading = ref(false)
const mentorLoadingFresh = ref(false)  // 深度分析(强制实时) 的 loading 状态
const mentorError = ref('')
const mentorAi = ref(false)
const mentorMode = ref('full')   // cached | incremental | full | fresh | empty
const mentorModal = ref(false)   // 毛玻璃弹窗展示

// 报告来源标签 (让用户清楚本次结果来自哪里、质量如何)
const mentorModeMeta = computed(() => ({
  cached:       { text: '⚡ 命中缓存', tip: '标签未变化，直接复用上次分析（0 token）', cls: 'bg-sky-100 dark:bg-sky-500/20 text-sky-600 dark:text-sky-400' },
  incremental:  { text: '🔁 增量更新', tip: '基于上次结论 + 本次标签增减做增量修订', cls: 'bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400' },
  full:         { text: '📝 全新生成', tip: '首次或长期未命中缓存，基于当前打标全量生成', cls: 'bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400' },
  fresh:        { text: '🧠 深度分析', tip: '你主动选择：忽略缓存，强制实时调大模型全新生成', cls: 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' },
  empty:        { text: '空', tip: '', cls: 'bg-gray-100 dark:bg-gray-700 text-gray-500' },
}[mentorMode.value] || { text: '生成', tip: '', cls: 'bg-gray-100 dark:bg-gray-700 text-gray-500' }))

async function askMentor(forceFresh = false) {
  mentorError.value = ''
  mentorLoading.value = true
  mentorLoadingFresh.value = forceFresh  // 区分两个按钮的 loading 文案
  try {
    // 兴趣技能地图默认只分析 interests; 其它维度则分析当前维度
    const target = dimension.value === 'interests' ? null : dimension.value
    const r = await fetch('/api/interest-map/mentor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dimension: target, force_fresh: forceFresh }),
    })
    const d = await r.json()
    if (d.code === 0) {
      mentorReport.value = d.data.report
      mentorAi.value = d.data.ai
      mentorMode.value = d.data.mode || 'full'
      mentorModal.value = true   // 生成完成自动弹出
    } else {
      mentorError.value = d.message || '生成失败'
    }
  } catch (e: any) {
    mentorError.value = e.message
  } finally {
    mentorLoading.value = false
    mentorLoadingFresh.value = false
  }
}

function closeMentorModal() {
  mentorModal.value = false
}

// 流程节点：1=能力画像  2=目标距离。复用同一面板，对应节点点亮
const activeStep = ref<'mentor' | 'goal'>('mentor')

// 目标距离结果也支持单独下载保存
function downloadGoal() {
  if (!goalResult.value) return
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  // 把 JSON 结果渲染为可读 Markdown
  let md = `# 目标路径距离测算\n\n`
  md += `> 目标：${goalResult.value.goal_input || goalText.value}\n\n`
  md += `> 来源：${goalModeMeta.value.text}\n\n`
  if (goalResult.value.mode === 'local-hard') {
    md += `${goalResult.value.message}\n\n`
    if (goalResult.value.distance !== null) {
      md += `- 最近能力节点：${goalResult.value.nearest}（${goalResult.value.nearest_mark}）\n`
      md += `- 树距离：${goalResult.value.distance} · ${goalResult.value.level}\n`
      if (goalResult.value.fill_path?.length)
        md += `- 最短补足路径：${goalResult.value.fill_path.join(' → ')}\n`
    }
  } else {
    if (goalResult.value.target_summary) md += `**目标点**：${goalResult.value.target_summary}\n\n`
    if (goalResult.value.target_archetypes?.length)
      md += `**目标态原型**：${goalResult.value.target_archetypes.join('、')}\n\n`
    if (goalResult.value.dimensions?.length) {
      md += `## 跨空间距离向量\n\n`
      for (const d of goalResult.value.dimensions) {
        md += `### ${d.name}（距离 ${d.nearest_distance}）\n`
        md += `- 含义：${d.meaning}\n`
        md += `- 所需：${d.required}\n`
        md += `- 隐性门槛：${d.hidden_barrier}\n`
        if (d.nearest_user_node) md += `- 最近能力节点：${d.nearest_user_node}\n`
        if (d.fill_path?.length) md += `- 补足路径：${d.fill_path.join(' → ')}\n`
        if (d.note) md += `- 备注：${d.note}\n`
        md += `\n`
      }
    }
    if (goalResult.value.approach_path?.length)
      md += `## 整体推进路径\n${goalResult.value.approach_path.join(' → ')}\n\n`
    if (goalResult.value.first_steps?.length) {
      md += `## 可立即开始的行动\n`
      for (const s of goalResult.value.first_steps) md += `- ${s}\n`
      md += `\n`
    }
    if (goalResult.value.baseline_note) md += `> ${goalResult.value.baseline_note}\n`
    if (goalResult.value.error) md += `\n> ⚠️ ${goalResult.value.error}\n`
  }
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `life-workbench-目标距离-${ts}.md`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(a.href)
}

// 下载画像报告为本地 Markdown 文件
function downloadMentor() {
  if (!mentorReport.value) return
  const dim = dimension.value === 'interests' ? '能力画像' : (DIM_META[dimension.value]?.name || '画像')
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  const blob = new Blob([mentorReport.value], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `life-workbench-${dim}-${ts}.md`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(a.href)
}

// 目标 → 路径距离 (语义投影解析)
const goalText = ref('')
const goalResult = ref<any>(null)
const goalLoading = ref(false)
const goalLoadingLlm = ref(false)   // 深度解析 (强制 LLM) 的 loading 状态
const goalError = ref('')

async function calcGoal(forceLlm = false) {
  if (!goalText.value.trim()) { goalError.value = '请先写下你的目标'; return }
  goalError.value = ''
  goalLoading.value = true
  goalLoadingLlm.value = forceLlm
  goalResult.value = null
  try {
    // 快速测算: 本地树距离; 深度解析: 强制 LLM 投影解析
    const target = dimension.value === 'interests' ? null : dimension.value
    const r = await fetch('/api/interest-map/goal-semantic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal: goalText.value.trim(), force_llm: forceLlm, dimension: target }),
    })
    const d = await r.json()
    if (d.code === 0) {
      goalResult.value = d.data
    } else {
      goalError.value = d.message || '计算失败'
    }
  } catch (e: any) {
    goalError.value = e.message
  } finally {
    goalLoading.value = false
    goalLoadingLlm.value = false
  }
}

// 目标结果来源标签 (让用户清楚本次结果来自哪里、质量如何)
const goalModeMeta = computed(() => ({
  'local-hard':    { text: '⚡ 本地树距离', tip: '目标在能力树上硬匹配成功，基于树距离实时计算（0 token，可解释）', cls: 'bg-sky-100 dark:bg-sky-500/20 text-sky-600 dark:text-sky-400' },
  'llm-semantic':  { text: '🧠 LLM 投影解析', tip: '你主动选择：强制实时调大模型把目标投影为能力维度 + 跨空间距离向量', cls: 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' },
  'local-fallback':{ text: '本地启发式', tip: '未配置 AI 或调用失败，基于关键词的本地启发式外推（仅供参考）', cls: 'bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400' },
}[(goalResult.value?.mode as string) || ''] || { text: '测算', tip: '', cls: 'bg-gray-100 dark:bg-gray-700 text-gray-500' }))

const goalModeLabel = (m?: string) => ({
  'local-hard': '本地树距离',
  'llm-semantic': 'LLM 投影解析',
  'local-fallback': '本地启发式解析',
}[m || ''] || '解析')

// 历史画像记录 (本地持久化, 供「查看历史」调用)
const historyModal = ref(false)
const historyList = ref<{
  id: string; created_at: string; mode: string; ai: boolean;
  preview: string; has_goal: boolean; goal_input: string; goal_mode: string
}[]>([])
const historyLoading = ref(false)

async function loadHistory() {
  historyLoading.value = true
  try {
    const dim = dimension.value === 'interests' ? 'all' : dimension.value
    const r = await fetch(`/api/interest-map/mentor-history?dimension=${encodeURIComponent(dim)}`)
    const d = await r.json()
    if (d.code === 0) historyList.value = d.data.list || []
  } finally {
    historyLoading.value = false
  }
}

function openHistory() {
  historyModal.value = true
  loadHistory()
}

function applyHistoryRecord(data: any) {
  // 载入画像报告
  mentorReport.value = data.report || ''
  mentorMode.value = data.mode || 'full'
  mentorAi.value = !!data.ai
  // 载入关联的目标测算 (若有)
  if (data.goal && data.goal.result) {
    goalResult.value = data.goal.result
    goalText.value = data.goal.goal_input || ''
    goalResult.value.goal_input = data.goal.goal_input || ''  // 供下载使用
    activeStep.value = 'goal'
  } else {
    goalResult.value = null
    activeStep.value = 'mentor'
  }
}

async function viewHistory(rec: { id: string }) {
  const dim = dimension.value === 'interests' ? 'all' : dimension.value
  const r = await fetch(`/api/interest-map/mentor-history/${encodeURIComponent(dim)}/${encodeURIComponent(rec.id)}`)
  const d = await r.json()
  if (d.code === 0) {
    applyHistoryRecord(d.data)
    historyModal.value = false
    mentorModal.value = true
  }
}

async function restoreLatestHistory() {
  await loadHistory()
  if (historyList.value.length) {
    const latest = historyList.value[0]
    const dim = dimension.value === 'interests' ? 'all' : dimension.value
    const r = await fetch(`/api/interest-map/mentor-history/${encodeURIComponent(dim)}/${encodeURIComponent(latest.id)}`)
    const d = await r.json()
    if (d.code === 0) {
      applyHistoryRecord(d.data)
    }
  }
}

const hasMentorRecord = computed(() => !!(mentorReport.value || historyList.value.length))

const markedCount = computed(() => Object.keys(marks).length)
const leafCount = computed(() => derived.value.leaves.length)

// 认知末梢级别: 把 levels (各状态达到的最大树深) 转成可读标签
// depth: 0=域级, 1=学科, 2=具体课程(末梢)
const levelLabel = (d: number) => d >= 2 ? '具体课程层' : d === 1 ? '学科层' : '领域层'
const stateLabel: Record<string, string> = { like: '感兴趣', skill: '精通', know: '听说过', want: '想学', learning: '在修', tried: '修过' }
const depthReached = computed(() => {
  const lv = derived.value.levels || {}
  return (['like', 'skill', 'know', 'want', 'learning', 'tried'] as const)
    .filter(s => typeof lv[s] === 'number')
    .map(s => ({ state: s, label: stateLabel[s], depth: lv[s], text: levelLabel(lv[s]) }))
})

// 维度切换时重置并重新加载
watch(dimension, async () => {
  trail.value = [{ id: null, name: '客观世界' }]
  currentParent.value = null
  Object.keys(marks).forEach(k => delete marks[k])
  Object.keys(customNodes).forEach(k => delete customNodes[k])
  mentorReport.value = ''
  goalResult.value = null
  goalText.value = ''
  await Promise.all([loadTree(null), loadMarks()])
  // 切换维度后自动恢复该维度的最新历史画像
  await restoreLatestHistory()
})

onMounted(async () => {
  await Promise.all([loadTree(null), loadMarks()])
  // 页面进入时自动拉取本地历史记录; 若当前内存尚无画像, 则自动恢复最新一条
  await loadHistory()
  if (!mentorReport.value) {
    await restoreLatestHistory()
  }
})
</script>

<template>
  <div class="max-w-5xl mx-auto animate-fade-in">
    <!-- 页头 -->
    <div class="mb-5 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <span>{{ meta.icon }}</span> {{ meta.name }}地图
        </h1>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {{ meta.intro }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="exportAll"
          class="px-3 py-2 rounded-xl text-xs font-medium bg-gradient-to-r from-violet-500 to-purple-500 text-white hover:from-violet-600 hover:to-purple-600 transition-colors shadow-sm whitespace-nowrap"
        >
          ⬇ 导出全部 (YAML)
        </button>
        <button
          @click="router.push('/profile')"
          class="px-3 py-2 rounded-xl text-xs font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
        >
          ← 返回画像
        </button>
      </div>
    </div>

    <!-- 维度切换 -->
    <div class="mb-4 flex items-center gap-2 flex-wrap">
      <button
        v-for="(m, key) in DIM_META" :key="key"
        @click="$router.push(`/interest-map?dim=${key}`)"
        class="px-3 py-1.5 rounded-xl text-xs font-medium transition-colors border"
        :class="dimension === key
          ? 'bg-primary-500 text-white border-primary-500 shadow-sm'
          : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'"
      >
        <span class="mr-1">{{ m.icon }}</span>{{ m.name }}
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- 左: 下钻树 -->
      <div class="lg:col-span-2 card p-5">
        <!-- 面包屑 -->
        <div class="flex items-center gap-1 flex-wrap text-xs mb-4">
          <button
            v-for="(t, i) in trail" :key="i"
            @click="goTrail(i)"
            class="px-2 py-1 rounded-lg transition-colors"
            :class="i === trail.length - 1
              ? 'bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 font-semibold'
              : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'"
          >
            {{ t.name }}
          </button>
        </div>

        <!-- 子节点列表 -->
        <div v-if="loading" class="space-y-2 animate-pulse">
          <div v-for="i in 5" :key="i" class="h-12 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="c in children" :key="c.id"
            class="group flex items-center gap-3 p-3 rounded-xl border transition-all"
            :class="(isMarked(c.id).like || isMarked(c.id).skill || isMarked(c.id).know || isMarked(c.id).want || isMarked(c.id).learning || isMarked(c.id).tried)
              ? (isMarked(c.id).tried
                ? 'border-amber-200 dark:border-amber-500/30 bg-amber-50/40 dark:bg-amber-500/5'
                : isMarked(c.id).learning
                ? 'border-sky-200 dark:border-sky-500/30 bg-sky-50/40 dark:bg-sky-500/5'
                : isMarked(c.id).want
                ? 'border-orange-200 dark:border-orange-500/30 bg-orange-50/40 dark:bg-orange-500/5'
                : isMarked(c.id).skill
                ? 'border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-500/5'
                : isMarked(c.id).like
                ? 'border-rose-200 dark:border-rose-500/30 bg-rose-50/40 dark:bg-rose-500/5'
                : 'border-slate-200 dark:border-slate-500/30 bg-slate-50/40 dark:bg-slate-500/5')
              : 'border-gray-100 dark:border-gray-700 hover:border-primary-200 dark:hover:border-primary-500/30'"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                {{ c.name }}
                <span v-if="c.custom" class="text-[9px] ml-1 px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-400">自定义</span>
                <span v-else-if="c.external" class="text-[9px] ml-1 px-1 py-0.5 rounded bg-sky-100 dark:bg-sky-500/20 text-sky-500">API</span>
              </p>
            </div>

            <!-- 打标按钮 (6 态可叠加: 关注/擅长/知道/想了解/在学/已体验) -->
            <div class="flex items-center gap-1 flex-shrink-0">
              <button
                @click="toggleMark(c.id, 'like')"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all"
                :class="isMarked(c.id).like
                  ? 'bg-rose-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-rose-500'"
                title="关注 / 感兴趣"
              >❤️</button>
              <button
                @click="toggleMark(c.id, 'skill')"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all"
                :class="isMarked(c.id).skill
                  ? 'bg-emerald-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-emerald-500'"
                title="擅长 / 有经验"
              >💪</button>
              <button
                @click="toggleMark(c.id, 'know')"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all"
                :class="isMarked(c.id).know
                  ? 'bg-slate-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-slate-500'"
                title="知道 / 听说过 (未参与)"
              >👁️</button>
              <button
                @click="toggleMark(c.id, 'want')"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all"
                :class="isMarked(c.id).want
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-orange-500'"
                title="想了解 / 意愿"
              >💡</button>
              <button
                @click="toggleMark(c.id, 'learning')"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all"
                :class="isMarked(c.id).learning
                  ? 'bg-sky-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-sky-500'"
                title="在学 / 进行中"
              >📚</button>
              <button
                @click="toggleMark(c.id, 'tried')"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-all"
                :class="isMarked(c.id).tried
                  ? 'bg-amber-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-amber-500'"
                title="已体验 / 经历过"
              >✅</button>
              <button
                v-if="c.has_children"
                @click="drill(c.id, c.name)"
                class="px-2.5 h-8 rounded-lg text-[10px] font-medium bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-500/20 transition-colors whitespace-nowrap"
              >下钻 ›</button>
            </div>
          </div>

          <p v-if="!children.length" class="text-xs text-gray-400 text-center py-6">
            {{ meta.leafHint }}
          </p>
        </div>

        <!-- 自定义细分 -->
        <div class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button
            v-if="!showCustomInput"
            @click="showCustomInput = true"
            class="text-[11px] text-primary-500 hover:underline font-medium"
          >+ 在当前「{{ trail[trail.length - 1].name }}」下自定义一个细分节点</button>
          <div v-else class="space-y-2">
            <input
              v-model="customName"
              @keyup.enter="addCustom"
              placeholder="例如：Rust 异步运行时 / 露营装备 / 爵士钢琴..."
              class="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500/30"
            />
            <div class="flex items-center gap-2">
              <button @click="addCustom" class="px-3 py-1.5 rounded-lg text-[10px] font-medium bg-primary-500 text-white hover:bg-primary-600">添加</button>
              <button @click="showCustomInput = false" class="px-3 py-1.5 rounded-lg text-[10px] text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700">取消</button>
              <span v-if="customError" class="text-[10px] text-red-500">{{ customError }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右: 兴趣图谱 -->
      <div class="space-y-4">
        <!-- 概览 -->
        <div class="card p-4 bg-gradient-to-br from-primary-50/50 to-purple-50/50 dark:from-primary-500/5 dark:to-purple-500/5">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ markedCount }}</p>
              <p class="text-[10px] text-gray-500">已打标节点</p>
            </div>
            <div class="text-right">
              <p class="text-2xl font-bold text-primary-600 dark:text-primary-400">{{ leafCount }}</p>
              <p class="text-[10px] text-gray-500">兴趣末梢</p>
            </div>
          </div>
          <p class="text-[10px] text-gray-400 mt-2 leading-relaxed">
            打标的节点会自动派生关键词，写入「{{ meta.name }}」画像，立即影响资讯/比价/周边推荐。
          </p>
        </div>

        <!-- AI 能力画像 -->
        <div class="card p-4 bg-gradient-to-br from-amber-50/60 to-rose-50/60 dark:from-amber-500/5 dark:to-rose-500/5">
          <h3 class="text-xs font-bold text-gray-900 dark:text-white mb-1 flex items-center gap-1">
            🧭 能力画像
          </h3>
          <p class="text-[10px] text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">
            基于你逐层下钻打标的整棵能力树，客观还原你当前的能力结构、可独立支撑的事项，以及潜力区/空白区——这是 AI 在你写下目标时计算「路径距离」的基线。
          </p>
          <div class="grid grid-cols-2 gap-2">
            <button
              @click="askMentor(false)"
              :disabled="mentorLoading"
              class="px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 transition-colors shadow-sm disabled:opacity-60"
              title="智能复用：标签没变秒回缓存，变了走增量，省 token"
            >
              <span v-if="mentorLoading && !mentorLoadingFresh">⚡ 快速生成中…</span>
              <span v-else>⚡ 快速画像</span>
            </button>
            <button
              @click="askMentor(true)"
              :disabled="mentorLoading"
              class="px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-rose-500 to-fuchsia-500 text-white hover:from-rose-600 hover:to-fuchsia-600 transition-colors shadow-sm disabled:opacity-60"
              :title="mentorAi ? '强制实时调大模型基于当前打标全新生成' : '当前未配置 AI，将走本地启发式总结'"
            >
              <span v-if="mentorLoading && mentorLoadingFresh">🧠 深度分析中…</span>
              <span v-else>🧠 深度分析</span>
            </button>
          </div>
          <p v-if="mentorError" class="text-[10px] text-red-500 mt-2">{{ mentorError }}</p>

          <!-- 已生成: 来源徽章 + 查看/下载入口 (避免长文撑爆卡片) -->
          <div
            v-if="hasMentorRecord && !mentorModal"
            class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center gap-2 flex-wrap"
          >
            <span class="text-[9px] px-1.5 py-0.5 rounded" :class="mentorModeMeta.cls" :title="mentorModeMeta.tip">{{ mentorModeMeta.text }}</span>
            <span v-if="mentorAi" class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">LLM 实时</span>
            <span v-else class="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">本地启发式</span>
            <button
              @click="mentorModal = true"
              class="ml-auto text-[10px] px-2 py-1 rounded-lg text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-500/10 transition-colors font-medium"
            >👁️ 查看</button>
            <button
              @click="openHistory"
              class="text-[10px] px-2 py-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="查看历史画像记录及其对应的目标测算"
            >📜 历史</button>
            <button
              @click="downloadMentor"
              class="text-[10px] px-2 py-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >⬇ 下载</button>
          </div>

          <!-- 目标 → 路径距离组件已移入「能力画像」弹窗内部 (基于画像上下文) -->
        </div>

        <!-- 认知末梢级别 (仅知识体系维度) -->
        <div class="card p-4" v-if="dimension === 'knowledge' && depthReached.length">
          <h3 class="text-xs font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-1">🎯 认知末梢级别</h3>
          <div class="space-y-1.5">
            <div
              v-for="r in depthReached" :key="r.state"
              class="flex items-center justify-between text-[10px]"
            >
              <span class="text-gray-500 dark:text-gray-400">{{ r.label }}</span>
              <span class="px-2 py-0.5 rounded-lg bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 font-medium">
                到达 {{ r.text }}
              </span>
            </div>
          </div>
          <p class="text-[10px] text-gray-400 mt-2 leading-relaxed">
            深度越高代表认知越接近具体课程末梢。可在左侧继续下钻打标以刷新此画像。
          </p>
        </div>

        <!-- 兴趣末梢 -->
        <div class="card p-4" v-if="derived.leaves.length">
          <h3 class="text-xs font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-1">🌿 兴趣末梢</h3>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="leaf in derived.leaves" :key="leaf.id"
              class="text-[10px] px-2 py-1 rounded-lg border flex items-center gap-1"
              :class="(leaf.mark?.tried
                ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/20'
                : leaf.mark?.learning
                ? 'bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-500/20'
                : leaf.mark?.want
                ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-500/20'
                : leaf.mark?.skill
                ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20'
                : leaf.mark?.like
                ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/20'
                : 'bg-slate-50 dark:bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-500/20')"
            ><span v-if="leaf.mark?.like">❤️</span><span v-if="leaf.mark?.skill">💪</span><span v-if="leaf.mark?.know">👁️</span><span v-if="leaf.mark?.want">💡</span><span v-if="leaf.mark?.learning">📚</span><span v-if="leaf.mark?.tried">✅</span>{{ leaf.name }}</span>
          </div>
        </div>

        <!-- 兴趣路径 -->
        <div class="card p-4" v-if="derived.paths.length">
          <h3 class="text-xs font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-1">🧭 兴趣路径</h3>
          <div class="space-y-1.5">
            <div
              v-for="(p, i) in derived.paths" :key="i"
              class="text-[10px] text-gray-600 dark:text-gray-400"
            >
              <span class="text-gray-400">
                <span v-if="p.mark?.like">❤️</span><span v-if="p.mark?.skill">💪</span><span v-if="p.mark?.know">👁️</span><span v-if="p.mark?.want">💡</span><span v-if="p.mark?.learning">📚</span><span v-if="p.mark?.tried">✅</span>
              </span>
              <span
                v-for="(seg, j) in p.path" :key="j"
                class="after:content-['›'] after:mx-1 after:text-gray-300 dark:after:text-gray-600"
              >{{ seg.name }}</span>
            </div>
          </div>
        </div>

        <!-- 派生关键词 -->
        <div class="card p-4">
          <h3 class="text-xs font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-1">🔑 派生关键词</h3>
          <div v-if="derived.keywords.length" class="flex flex-wrap gap-1.5">
            <span
              v-for="kw in derived.keywords" :key="kw"
              class="text-[10px] px-2 py-0.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400 border border-gray-100 dark:border-gray-600"
            >{{ kw }}</span>
          </div>
          <p v-else class="text-[10px] text-gray-400">暂未打标。去左侧世界树上点亮你感兴趣的节点吧。</p>
        </div>

        <!-- 知道 / 想了解 / 在学 / 已体验 -->
        <div v-if="derived.know?.length || derived.want?.length || derived.learning?.length || derived.tried?.length" class="space-y-3">
          <div v-if="derived.know?.length" class="card p-4">
            <h3 class="text-xs font-bold text-slate-600 dark:text-slate-400 mb-2 flex items-center gap-1">👁️ 知道 / 听说过</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="k in derived.know" :key="k" class="text-[10px] px-2 py-0.5 rounded-lg bg-slate-50 dark:bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-500/20">{{ k }}</span>
            </div>
          </div>
          <div v-if="derived.want?.length" class="card p-4">
            <h3 class="text-xs font-bold text-orange-600 dark:text-orange-400 mb-2 flex items-center gap-1">💡 想了解</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="w in derived.want" :key="w" class="text-[10px] px-2 py-0.5 rounded-lg bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-200 dark:border-orange-500/20">{{ w }}</span>
            </div>
          </div>
          <div v-if="derived.learning?.length" class="card p-4">
            <h3 class="text-xs font-bold text-sky-600 dark:text-sky-400 mb-2 flex items-center gap-1">📚 在学</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="l in derived.learning" :key="l" class="text-[10px] px-2 py-0.5 rounded-lg bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-200 dark:border-sky-500/20">{{ l }}</span>
            </div>
          </div>
          <div v-if="derived.tried?.length" class="card p-4">
            <h3 class="text-xs font-bold text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-1">✅ 已体验</h3>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="t in derived.tried" :key="t" class="text-[10px] px-2 py-0.5 rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">{{ t }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 能力画像 · 毛玻璃弹窗 ========== -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="mentorModal"
          class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          @click.self="closeMentorModal"
        >
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-pointer" @click="closeMentorModal"></div>

          <div class="relative w-full max-w-3xl max-h-[88vh] flex flex-col rounded-2xl bg-white/95 dark:bg-gray-800/95 shadow-2xl border border-white/20 dark:border-gray-700/50 animate-slide-up">
            <!-- 标题栏 -->
            <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-lg">🧭</span>
                <h3 class="text-sm font-bold text-gray-900 dark:text-white">我的能力画像</h3>
                <span class="text-[9px] px-1.5 py-0.5 rounded" :class="mentorModeMeta.cls" :title="mentorModeMeta.tip">{{ mentorModeMeta.text }}</span>
                <span v-if="mentorAi" class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">LLM 实时</span>
                <span v-else class="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">本地启发式</span>
                <button
                  @click="openHistory"
                  class="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  title="查看历史画像记录及其对应的目标测算"
                >📜 历史</button>
              </div>
              <button
                @click="closeMentorModal"
                class="w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- 流程节点步骤条 -->
            <div class="flex items-stretch gap-2 px-5 py-3 border-b border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40">
              <button
                @click="activeStep = 'mentor'"
                class="flex-1 flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] font-semibold transition-all border"
                :class="activeStep === 'mentor'
                  ? 'bg-primary-500 text-white border-primary-500 shadow-sm'
                  : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-primary-300'"
              >
                <span class="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold"
                  :class="mentorReport
                    ? (activeStep === 'mentor' ? 'bg-white/25 text-white' : 'bg-primary-500 text-white')
                    : (activeStep === 'mentor' ? 'bg-white/25 text-white' : 'bg-gray-300 dark:bg-gray-600 text-white')">
                  {{ mentorReport ? '✓' : '1' }}
                </span>
                能力画像
              </button>
              <div class="self-center text-gray-300 dark:text-gray-600 text-xs">→</div>
              <button
                @click="activeStep = 'goal'"
                class="flex-1 flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] font-semibold transition-all border"
                :class="activeStep === 'goal'
                  ? 'bg-primary-500 text-white border-primary-500 shadow-sm'
                  : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-primary-300'"
              >
                <span class="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold"
                  :class="goalResult
                    ? (activeStep === 'goal' ? 'bg-white/25 text-white' : 'bg-primary-500 text-white')
                    : (activeStep === 'goal' ? 'bg-white/25 text-white' : 'bg-gray-300 dark:bg-gray-600 text-white')">
                  {{ goalResult ? '✓' : '2' }}
                </span>
                目标距离
              </button>
            </div>

            <!-- 可滚动内容区 -->
            <div class="flex-1 overflow-y-auto px-5 py-4">

              <!-- 流程面板 1：能力画像 -->
              <div v-show="activeStep === 'mentor'" class="space-y-3">
                <!-- 生成按钮区 (未生成时展示; 生成后折叠为顶部长条) -->
                <div v-if="!mentorReport" class="flex flex-col items-center gap-3 py-6">
                  <p class="text-[11px] text-gray-400 text-center px-6">
                    基于你当前的打标，生成一份客观的能力结构画像。
                  </p>
                  <div class="grid grid-cols-2 gap-2 w-full max-w-xs">
                    <button
                      @click="askMentor(false)"
                      :disabled="mentorLoading"
                      class="px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 transition-colors shadow-sm disabled:opacity-60"
                    >
                      <span v-if="mentorLoading && !mentorLoadingFresh">⚡ 生成中…</span>
                      <span v-else>⚡ 快速画像</span>
                    </button>
                    <button
                      @click="askMentor(true)"
                      :disabled="mentorLoading"
                      class="px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-rose-500 to-fuchsia-500 text-white hover:from-rose-600 hover:to-fuchsia-600 transition-colors shadow-sm disabled:opacity-60"
                      :title="mentorAi ? '强制实时调大模型基于当前打标全新生成' : '当前未配置 AI，将走本地启发式总结'"
                    >
                      <span v-if="mentorLoading && mentorLoadingFresh">🧠 生成中…</span>
                      <span v-else>🧠 深度分析</span>
                    </button>
                  </div>
                </div>

                <div v-else>
                  <!-- 画像来源行 + 重生成/下载 -->
                  <div class="flex items-center gap-2 flex-wrap mb-2">
                    <span class="text-[9px] px-1.5 py-0.5 rounded" :class="mentorModeMeta.cls" :title="mentorModeMeta.tip">{{ mentorModeMeta.text }}</span>
                    <span v-if="mentorAi" class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">LLM 实时</span>
                    <span v-else class="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">本地启发式</span>
                    <div class="ml-auto flex items-center gap-1.5">
                      <button @click="askMentor(false)" :disabled="mentorLoading" class="text-[10px] px-2 py-1 rounded-lg bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 hover:opacity-90 disabled:opacity-60" title="重新快速生成">⚡ 重生成</button>
                      <button @click="askMentor(true)" :disabled="mentorLoading" class="text-[10px] px-2 py-1 rounded-lg bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 hover:opacity-90 disabled:opacity-60" title="重新深度分析">🧠 深度</button>
                      <button @click="downloadMentor" class="text-[10px] px-2 py-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">⬇ 下载</button>
                    </div>
                  </div>
                  <div class="text-[12px] leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans">
{{ mentorReport }}
                  </div>
                </div>
              </div>

              <!-- 流程面板 2：目标 → 路径距离 -->
              <div v-show="activeStep === 'goal'" class="space-y-3">
                <h4 class="text-[11px] font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-1">
                  🎯 基于以上画像，写下你的目标，计算路径距离
                </h4>
                <input
                  v-model="goalText"
                  @keyup.enter="calcGoal(false)"
                  placeholder="例如：用 Rust 写一个嵌入式操作系统 / 做一款独立游戏"
                  class="w-full px-3 py-2 text-[11px] rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500/30"
                />
                <div class="grid grid-cols-2 gap-2 mt-2">
                  <button
                    @click="calcGoal(false)"
                    :disabled="goalLoading"
                    class="px-3 py-1.5 rounded-xl text-[11px] font-medium bg-gray-900 dark:bg-white dark:text-gray-900 text-white hover:opacity-90 transition-opacity disabled:opacity-60"
                    title="本地树距离：目标在能力树上硬匹配则秒回，0 token 可解释"
                  >
                    <span v-if="goalLoading && !goalLoadingLlm">⚡ 测算中…</span>
                    <span v-else>⚡ 快速测算</span>
                  </button>
                  <button
                    @click="calcGoal(true)"
                    :disabled="goalLoading"
                    class="px-3 py-1.5 rounded-xl text-[11px] font-medium bg-gradient-to-r from-rose-500 to-fuchsia-500 text-white hover:from-rose-600 hover:to-fuchsia-600 transition-colors disabled:opacity-60"
                    title="强制实时调大模型把目标投影为能力维度 + 跨空间距离向量（未配置 AI 时自动降级为本地启发式）"
                  >
                    <span v-if="goalLoading && goalLoadingLlm">🧠 解析中…</span>
                    <span v-else>🧠 深度解析</span>
                  </button>
                </div>
                <p v-if="goalError" class="text-[10px] text-red-500 mt-2">{{ goalError }}</p>
                <div
                  v-if="goalResult"
                  class="mt-3 p-3 rounded-xl bg-gray-50 dark:bg-gray-800/60 text-[11px] leading-relaxed text-gray-700 dark:text-gray-300"
                >
                  <!-- 目标结果来源行 + 重测算/深度/下载 -->
                  <div class="flex items-center gap-2 flex-wrap mb-2">
                    <span class="text-[9px] px-1.5 py-0.5 rounded" :class="goalModeMeta.cls" :title="goalModeMeta.tip">{{ goalModeMeta.text }}</span>
                    <span v-if="goalResult.ai" class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">LLM 实时</span>
                    <span v-else class="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">本地启发式</span>
                    <div class="ml-auto flex items-center gap-1.5">
                      <button @click="calcGoal(false)" :disabled="goalLoading" class="text-[10px] px-2 py-1 rounded-lg bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 hover:opacity-90 disabled:opacity-60" title="重新快速测算">⚡ 重测算</button>
                      <button @click="calcGoal(true)" :disabled="goalLoading" class="text-[10px] px-2 py-1 rounded-lg bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 hover:opacity-90 disabled:opacity-60" title="重新深度解析">🧠 深度</button>
                      <button @click="downloadGoal" class="text-[10px] px-2 py-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">⬇ 下载</button>
                    </div>
                  </div>

                  <p class="font-semibold text-gray-900 dark:text-white mb-2">
                    📐 {{ goalResult.mode === 'local-hard' ? '路径距离分析' : '目标投影解析 · 跨空间距离向量' }}
                    <span v-if="goalResult.focus_dimension" class="text-[9px] font-normal text-gray-400 ml-1">· 聚焦 {{ DIM_META[goalResult.focus_dimension]?.name || goalResult.focus_dimension }}</span>
                  </p>

                  <!-- 本地硬匹配模式 -->
                  <template v-if="goalResult.mode === 'local-hard'">
                    <p>{{ goalResult.message }}</p>
                    <div v-if="goalResult.distance !== null" class="mt-2 space-y-1">
                      <p><span class="text-gray-500">最近能力节点：</span>{{ goalResult.nearest }}（{{ goalResult.nearest_mark }}）</p>
                      <p><span class="text-gray-500">树距离：</span>{{ goalResult.distance }} · {{ goalResult.level }}</p>
                      <p v-if="goalResult.fill_path && goalResult.fill_path.length">
                        <span class="text-gray-500">最短补足路径：</span>
                        <span class="text-primary-600 dark:text-primary-400">{{ goalResult.fill_path.join(' → ') }}</span>
                      </p>
                    </div>
                  </template>

                  <!-- 语义解析模式 (本地硬匹配失败 / LLM 投影) -->
                  <template v-else>
                    <p v-if="goalResult.target_summary" class="mb-2">
                      <span class="text-gray-500">目标点：</span>{{ goalResult.target_summary }}
                    </p>
                    <div v-if="goalResult.target_archetypes && goalResult.target_archetypes.length" class="mb-2">
                      <span class="text-gray-500">目标态原型：</span>
                      <span class="text-primary-600 dark:text-primary-400">{{ goalResult.target_archetypes.join('、') }}</span>
                    </div>

                    <p v-if="goalResult.dimensions && goalResult.dimensions.length" class="text-[10px] font-semibold text-gray-700 dark:text-gray-200 mb-1">跨空间距离向量</p>
                    <div v-for="(dim, i) in (goalResult.dimensions || [])" :key="i" class="mb-2 pb-2 border-b border-gray-200/60 dark:border-gray-700/60 last:border-0">
                      <div class="flex items-center justify-between">
                        <span class="font-medium text-gray-900 dark:text-white">{{ dim.name }}</span>
                        <span class="text-[9px] px-1.5 py-0.5 rounded"
                          :class="dim.nearest_distance === 0 ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600'
                            : dim.nearest_distance <= 2 ? 'bg-sky-100 dark:bg-sky-500/20 text-sky-600'
                            : dim.nearest_distance <= 4 ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-600'
                            : 'bg-rose-100 dark:bg-rose-500/20 text-rose-600'">
                          距离 {{ dim.nearest_distance }}
                        </span>
                      </div>
                      <p class="text-gray-500 mt-0.5">{{ dim.meaning }}</p>
                      <p class="mt-0.5"><span class="text-gray-400">所需：</span>{{ dim.required }}</p>
                      <p class="mt-0.5"><span class="text-gray-400">隐性门槛：</span>{{ dim.hidden_barrier }}</p>
                      <p class="mt-0.5" v-if="dim.nearest_user_node">
                        <span class="text-gray-400">最近能力节点：</span>{{ dim.nearest_user_node }}
                      </p>
                      <p class="mt-0.5" v-if="dim.fill_path && dim.fill_path.length">
                        <span class="text-gray-400">补足路径：</span>
                        <span class="text-primary-600 dark:text-primary-400">{{ dim.fill_path.join(' → ') }}</span>
                      </p>
                      <p class="mt-0.5 text-gray-400" v-if="dim.note">↳ {{ dim.note }}</p>
                    </div>

                    <div v-if="goalResult.approach_path && goalResult.approach_path.length" class="mt-2">
                      <p class="text-[10px] font-semibold text-gray-700 dark:text-gray-200 mb-1">整体推进路径</p>
                      <p>{{ goalResult.approach_path.join(' → ') }}</p>
                    </div>
                    <div v-if="goalResult.first_steps && goalResult.first_steps.length" class="mt-2">
                      <p class="text-[10px] font-semibold text-gray-700 dark:text-gray-200 mb-1">可立即开始的行动</p>
                      <ul class="list-disc list-inside space-y-0.5">
                        <li v-for="(s, i) in goalResult.first_steps" :key="i">{{ s }}</li>
                      </ul>
                    </div>
                    <p v-if="goalResult.baseline_note" class="mt-2 text-[9px] text-gray-400 leading-relaxed">{{ goalResult.baseline_note }}</p>
                    <p v-if="goalResult.error" class="mt-2 text-[9px] text-amber-500 leading-relaxed">⚠️ {{ goalResult.error }}</p>
                  </template>
                </div>

              </div>
            </div>

            <!-- 底部操作 -->
            <div class="flex items-center justify-between px-5 py-3 border-t border-gray-100 dark:border-gray-700">
              <p class="text-[10px] text-gray-400">每个流程节点的内容均可单独下载保存</p>
              <div class="flex items-center gap-2">
                <button
                  @click="closeMentorModal"
                  class="px-4 py-2 text-xs font-medium rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors shadow-sm"
                >关闭</button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ========== 历史画像记录 · 毛玻璃弹窗 ========== -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="historyModal"
          class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          @click.self="historyModal = false"
        >
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-pointer" @click="historyModal = false"></div>

          <div class="relative w-full max-w-lg max-h-[82vh] flex flex-col rounded-2xl bg-white/95 dark:bg-gray-800/95 shadow-2xl border border-white/20 dark:border-gray-700/50 animate-slide-up">
            <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
              <div class="flex items-center gap-2">
                <span class="text-lg">📜</span>
                <h3 class="text-sm font-bold text-gray-900 dark:text-white">历史画像记录</h3>
                <span class="text-[9px] text-gray-400">（本地保有，含对应目标测算）</span>
              </div>
              <button
                @click="historyModal = false"
                class="w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div class="flex-1 overflow-y-auto px-5 py-4">
              <p v-if="historyLoading" class="text-[11px] text-gray-400 text-center py-8">加载中…</p>
              <p v-else-if="!historyList.length" class="text-[11px] text-gray-400 text-center py-8">
                暂无历史画像记录。生成一份能力画像（或测算目标距离）后，会自动保存在这里。
              </p>
              <div v-else class="space-y-2">
                <button
                  v-for="rec in historyList" :key="rec.id"
                  @click="viewHistory(rec)"
                  class="w-full text-left p-3 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-500/40 hover:bg-primary-50/40 dark:hover:bg-primary-500/5 transition-colors"
                >
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-[10px] font-semibold text-gray-700 dark:text-gray-200">{{ rec.created_at }}</span>
                    <span v-if="rec.mode" class="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">{{ {cached:'命中缓存',incremental:'增量更新',full:'全新生成',fresh:'深度分析'}[rec.mode] || rec.mode }}</span>
                    <span v-if="rec.ai" class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">LLM</span>
                    <span v-if="rec.has_goal" class="text-[9px] px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400">含目标测算</span>
                  </div>
                  <p v-if="rec.preview" class="text-[10px] text-gray-500 dark:text-gray-400 mt-1 leading-relaxed line-clamp-2">{{ rec.preview }}</p>
                  <p v-if="rec.has_goal && rec.goal_input" class="text-[10px] text-primary-600 dark:text-primary-400 mt-1 truncate">🎯 {{ rec.goal_input }}</p>
                </button>
              </div>
            </div>

            <div class="flex items-center justify-between px-5 py-3 border-t border-gray-100 dark:border-gray-700">
              <p class="text-[10px] text-gray-400">点击任意记录即可调取该次画像与对应目标测算</p>
              <button
                @click="historyModal = false"
                class="px-4 py-2 text-xs font-medium rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors shadow-sm"
              >关闭</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
