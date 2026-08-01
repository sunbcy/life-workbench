<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import type { ProfileSummary } from '@/types'

const { data: profile, loading, error, refetch: reloadProfile } = useApi<ProfileSummary>('/profile/summary')

// Track which dimensions are expanded
const expandedDims = ref<Record<string, boolean>>({})

function toggleExpand(key: string) {
  expandedDims.value[key] = !expandedDims.value[key]
}

// Reload profile from disk
const reloading = ref(false)
async function onReload() {
  reloading.value = true
  try {
    await fetch('/api/profile/reload', { method: 'POST' })
    await reloadProfile()
  } finally {
    reloading.value = false
  }
}

// ========== YAML 编辑器 ==========
const editingDim = ref<string | null>(null)
const editingName = ref('')
const yamlContent = ref('')
const isNewFile = ref(false)
const yamlError = ref<string | null>(null)
const saving = ref(false)
const savedMsg = ref('')

function openEditor(dimKey: string, dimName: string) {
  editingDim.value = dimKey
  editingName.value = dimName
  yamlContent.value = ''
  isNewFile.value = false
  yamlError.value = null
  savedMsg.value = ''

  // 加载 YAML 内容（文件不存在时后端返回模板）
  fetch(`/api/profile/raw/${dimKey}`)
    .then(r => r.json())
    .then(d => {
      if (d.code === 0) {
        yamlContent.value = d.data.content
        isNewFile.value = d.data.is_new || false
      }
    })
    .catch(e => {
      yamlError.value = '加载失败: ' + e.message
    })
}

function closeEditor() {
  editingDim.value = null
  yamlContent.value = ''
  isNewFile.value = false
  yamlError.value = null
  savedMsg.value = ''
}

async function saveYaml() {
  if (!editingDim.value) return
  saving.value = true
  yamlError.value = null
  savedMsg.value = ''

  try {
    const r = await fetch(`/api/profile/raw/${editingDim.value}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: yamlContent.value }),
    })
    const d = await r.json()
    if (d.code === 0) {
      savedMsg.value = '✅ 已保存并重载'
      isNewFile.value = false
      await reloadProfile()
      setTimeout(closeEditor, 1500)
    } else {
      yamlError.value = d.detail || d.message || '保存失败'
    }
  } catch (e: any) {
    yamlError.value = e.message || '网络错误'
  } finally {
    saving.value = false
  }
}

// ========== 一键初始化 ==========
const initLoading = ref(false)
const initMsg = ref('')

async function initAll() {
  initLoading.value = true
  initMsg.value = ''
  try {
    const r = await fetch('/api/profile/init-all', { method: 'POST' })
    const d = await r.json()
    if (d.code === 0) {
      initMsg.value = `✅ ${d.message}`
      await reloadProfile()
    } else {
      initMsg.value = `❌ ${d.detail || d.message || '初始化失败'}`
    }
  } catch (e: any) {
    initMsg.value = '❌ ' + (e.message || '网络错误')
  } finally {
    initLoading.value = false
  }
}

function tierLabel(tier: string): string {
  return {
    core: '核心维度',
    important: '重要维度',
    auxiliary: '辅助维度',
    reference: '参考维度',
  }[tier] || tier
}

function tierBadgeClass(tier: string): string {
  return {
    core: 'bg-red-100 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/20',
    important: 'bg-amber-100 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/20',
    auxiliary: 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20',
    reference: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
  }[tier] || ''
}

function weightBarClass(weight: number): string {
  if (weight >= 0.25) return 'bg-gradient-to-r from-red-500 to-rose-500'
  if (weight >= 0.12) return 'bg-gradient-to-r from-amber-500 to-orange-500'
  if (weight >= 0.08) return 'bg-gradient-to-r from-emerald-500 to-green-500'
  return 'bg-gradient-to-r from-gray-400 to-gray-500'
}
</script>

<template>
  <div class="max-w-4xl mx-auto animate-fade-in">
    <!-- 页头 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <span>🧬</span> 我的画像
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        基于本地 profile 文件构建的个人画像。
        <span class="text-primary-500">隐私优先：所有数据仅存储在你的设备上。</span>
      </p>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 7" :key="i" class="card p-5 animate-pulse">
        <div class="h-20 bg-gray-100 dark:bg-gray-700 rounded-xl"></div>
      </div>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="card p-8 text-center">
      <p class="text-4xl mb-3">⚠️</p>
      <p class="text-sm text-gray-500">无法加载画像，请确保后端已启动</p>
    </div>

    <!-- 维度列表 -->
    <div v-else-if="profile" class="space-y-4">
      <!-- 未配置提示横幅 -->
      <div
        v-if="profile.activated_count === 0"
        class="card p-5 sm:p-6 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-500/5 dark:to-orange-500/5 border-amber-200 dark:border-amber-500/20"
      >
        <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <span class="text-4xl">🚀</span>
          <div class="flex-1">
            <h3 class="text-sm font-bold text-amber-800 dark:text-amber-300">尚未配置个人画像</h3>
            <p class="text-xs text-amber-600 dark:text-amber-400 mt-1">
              画像数据是推荐系统的基础。配置后可以获得个性化的资讯推荐、比价排序和周边资源推荐。
              所有数据仅存储在你的设备上，完全隐私。
            </p>
          </div>
          <div class="flex flex-col items-center gap-2">
            <button
              @click="initAll"
              :disabled="initLoading"
              class="px-5 py-2.5 rounded-xl text-xs font-bold bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-60 transition-colors shadow-sm whitespace-nowrap"
            >
              {{ initLoading ? '⏳ 初始化中...' : '🚀 一键初始化全部维度' }}
            </button>
            <span v-if="initMsg" class="text-[10px] text-amber-600 dark:text-amber-400">{{ initMsg }}</span>
          </div>
        </div>
      </div>

      <!-- 概览卡片 -->
      <div class="card p-5 bg-gradient-to-br from-primary-50/50 to-purple-50/50 dark:from-primary-500/5 dark:to-purple-500/5">
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <p class="text-2xl font-bold text-gray-900 dark:text-white">
              {{ profile.activated_count }} / {{ profile.dimensions.length }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">维度已激活</p>
          </div>
          <div class="text-right">
            <p class="text-sm font-semibold text-primary-600 dark:text-primary-400">
              总权重 {{ (profile.total_weight * 100).toFixed(0) }}%
            </p>
            <p class="text-[10px] text-gray-400 mt-1">推荐效果: {{ profile.total_weight >= 0.8 ? '优秀' : profile.total_weight >= 0.5 ? '良好' : '基础' }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="profile.activated_count < profile.dimensions.length"
              @click="initAll"
              :disabled="initLoading"
              class="px-3 py-2 rounded-xl text-[10px] font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors whitespace-nowrap"
            >
              {{ initLoading ? '⏳' : '🚀' }} 补全缺失维度
            </button>
            <button
              @click="onReload"
              :disabled="reloading"
              class="px-4 py-2 rounded-xl text-xs font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            >
              {{ reloading ? '⏳ 加载中...' : '🔄 重新加载' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 各维度详情 -->
      <div
        v-for="dim in profile.dimensions"
        :key="dim.key"
        class="card p-5 group"
      >
        <div class="flex items-start gap-4">
          <!-- 图标 -->
          <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0"
            :class="dim.active
              ? 'bg-white dark:bg-gray-700 shadow-sm border border-gray-100 dark:border-gray-600'
              : 'bg-gray-50 dark:bg-gray-700/50 opacity-50'"
          >
            {{ dim.icon }}
          </div>

          <!-- 信息 -->
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="text-sm font-bold text-gray-900 dark:text-white">{{ dim.name }}</h3>
              <span :class="tierBadgeClass(dim.tier)" class="text-[9px] px-1.5 py-0.5 rounded-md border font-medium">
                {{ tierLabel(dim.tier) }}
              </span>
              <span v-if="!dim.active" class="text-[9px] bg-gray-100 dark:bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded-md">
                未激活
              </span>
            </div>

            <!-- 权重条 -->
            <div class="flex items-center gap-2 mb-2">
              <div class="flex-1 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div
                  :class="weightBarClass(dim.weight)"
                  class="h-full rounded-full transition-all duration-500"
                  :style="{ width: `${dim.weight * 100}%` }"
                ></div>
              </div>
              <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 w-10 text-right">
                {{ dim.weight_pct }}
              </span>
            </div>

            <!-- 亮点标签 - 展开/折叠 -->
            <div class="flex gap-1.5 flex-wrap mt-2">
              <template v-for="(h, idx) in dim.highlights" :key="idx">
                <span
                  v-if="idx < 3 || expandedDims[dim.key]"
                  class="text-[10px] px-2 py-0.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400 border border-gray-100 dark:border-gray-600"
                >
                  {{ h }}
                </span>
              </template>
              <button
                v-if="dim.highlights.length > 3"
                @click="toggleExpand(dim.key)"
                class="text-[10px] px-2 py-0.5 rounded-lg text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-500/10 transition-colors font-medium"
              >
                {{ expandedDims[dim.key] ? '收起 ▲' : `展开全部 (${dim.highlights.length}) ▼` }}
              </button>
              <span v-if="!dim.active" class="text-[10px] text-gray-400 italic">
                编辑 ~/.life-workbench/profile/{{ dim.key }}.yaml 激活此维度
              </span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex flex-col items-center gap-1.5 flex-shrink-0">
            <!-- 支持「世界树下钻」的维度: 额外入口「探索地图」 -->
            <button
              v-if="dim.key === 'interests'"
              @click="$router.push('/interest-map')"
              class="px-3 py-1.5 rounded-lg text-[10px] font-medium bg-gradient-to-r from-emerald-500 to-green-500 text-white hover:from-emerald-600 hover:to-green-600 transition-colors whitespace-nowrap shadow-sm"
            >
              🌳 探索兴趣地图
            </button>
            <button
              v-else-if="dim.key === 'health'"
              @click="$router.push('/interest-map?dim=health')"
              class="px-3 py-1.5 rounded-lg text-[10px] font-medium bg-gradient-to-r from-rose-500 to-pink-500 text-white hover:from-rose-600 hover:to-pink-600 transition-colors whitespace-nowrap shadow-sm"
            >
              🩺 探索健康地图
            </button>
            <button
              v-else-if="dim.key === 'location'"
              @click="$router.push('/interest-map?dim=location')"
              class="px-3 py-1.5 rounded-lg text-[10px] font-medium bg-gradient-to-r from-sky-500 to-blue-500 text-white hover:from-sky-600 hover:to-blue-600 transition-colors whitespace-nowrap shadow-sm"
            >
              🗺️ 探索地理地图
            </button>
            <button
              v-else-if="dim.key === 'knowledge'"
              @click="$router.push('/interest-map?dim=knowledge')"
              class="px-3 py-1.5 rounded-lg text-[10px] font-medium bg-gradient-to-r from-violet-500 to-purple-500 text-white hover:from-violet-600 hover:to-purple-600 transition-colors whitespace-nowrap shadow-sm"
            >
              📚 探索知识地图
            </button>
            <!-- 未激活：显眼的配置按钮 -->
            <button
              v-if="!dim.active"
              @click="openEditor(dim.key, dim.name)"
              class="px-3 py-1.5 rounded-lg text-[10px] font-medium bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 border border-primary-200 dark:border-primary-500/20 hover:bg-primary-100 dark:hover:bg-primary-500/20 transition-colors whitespace-nowrap"
            >
              ✏️ 配置
            </button>
            <!-- 已激活：hover显示编辑按钮 -->
            <button
              v-else
              @click="openEditor(dim.key, dim.name)"
              class="opacity-0 group-hover:opacity-100 transition-all w-7 h-7 flex items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-500/10"
              title="编辑此维度"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 底部提示 -->
      <div class="card p-5 bg-gray-50/50 dark:bg-gray-800/50">
        <div class="flex items-start gap-3">
          <span class="text-lg">💡</span>
          <div>
            <p class="text-xs font-medium text-gray-700 dark:text-gray-300">如何修改画像？</p>
            <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
              点击每个维度的 <span class="text-primary-500">✏️ 编辑按钮</span> 可在线编辑 YAML 配置，
              或直接编辑 <code class="text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-500/10 px-1 rounded">~/.life-workbench/profile/</code> 目录下的文件。
              保存后自动热重载，无需重启。
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== YAML 编辑器弹窗 ========== -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="editingDim"
          class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4"
          @click.self="closeEditor"
        >
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-pointer" @click="closeEditor"></div>

          <div class="relative w-full max-w-2xl max-h-[90vh] card flex flex-col animate-slide-up">
            <!-- 标题栏 -->
            <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-lg">✏️</span>
                <h3 class="text-sm font-bold text-gray-900 dark:text-white">编辑「{{ editingName }}」</h3>
                <span class="text-[10px] text-gray-400">{{ editingDim }}.yaml</span>
                <span
                  v-if="isNewFile"
                  class="text-[9px] px-1.5 py-0.5 rounded-md bg-amber-100 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 font-medium"
                >
                  🆕 从模板创建
                </span>
              </div>
              <button
                @click="closeEditor"
                class="w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- 编辑器 -->
            <div class="flex-1 overflow-y-auto p-5">
              <textarea
                v-model="yamlContent"
                class="w-full h-[55vh] sm:h-[60vh] p-4 text-xs sm:text-sm font-mono rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 resize-none leading-relaxed"
                placeholder="加载中..."
                spellcheck="false"
              ></textarea>

              <!-- 错误提示 -->
              <div v-if="yamlError" class="mt-3 p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20">
                <p class="text-xs text-red-600 dark:text-red-400">{{ yamlError }}</p>
              </div>

              <!-- 成功提示 -->
              <div v-if="savedMsg" class="mt-3 p-3 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20">
                <p class="text-xs text-green-600 dark:text-green-400">{{ savedMsg }}</p>
              </div>
            </div>

            <!-- 底部按钮 -->
            <div class="flex items-center justify-between px-5 py-4 border-t border-gray-100 dark:border-gray-700">
              <p class="text-[10px] text-gray-400">
                💡 修改后点击保存，推荐引擎将自动重载新配置
              </p>
              <div class="flex items-center gap-2">
                <button
                  @click="closeEditor"
                  class="px-4 py-2.5 text-xs font-medium rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  取消
                </button>
                <button
                  @click="saveYaml"
                  :disabled="saving"
                  class="px-5 py-2.5 text-xs font-medium rounded-xl bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-60 transition-colors shadow-sm"
                >
                  {{ saving ? '⏳ 保存中...' : '💾 保存并重载' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
