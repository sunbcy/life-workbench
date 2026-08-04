<script setup lang="ts">
import { ref, reactive } from 'vue'

// 配置从后端加载（即本地 config.yaml 的完整内容）
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const message = ref('')

// 用 reactive 承载可编辑配置树（深拷贝后端返回）
const config = reactive<any>({})
const loaded = ref(false)

async function loadConfig() {
  loading.value = true
  error.value = null
  message.value = ''
  try {
    const res = await fetch('/api/config')
    const json = await res.json()
    if (json.code !== 0) throw new Error(json.message || '加载失败')
    // 清空并深拷贝
    for (const k of Object.keys(config)) delete config[k]
    Object.assign(config, JSON.parse(JSON.stringify(json.data)))
    loaded.value = true
    syncPresetHighlight()
  } catch (e: any) {
    error.value = e?.message || '网络错误'
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  error.value = null
  message.value = ''
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    const json = await res.json()
    if (json.code !== 0) throw new Error(json.message || '保存失败')
    message.value = '✅ ' + (json.message || '已保存')
  } catch (e: any) {
    error.value = e?.message || '网络错误'
  } finally {
    saving.value = false
  }
}

// 把数字/布尔/字符串按类型渲染；对象/数组递归渲染
function isObject(v: any) {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}
function isArray(v: any) {
  return Array.isArray(v)
}
function isBool(v: any) {
  return typeof v === 'boolean'
}
function isNumber(v: any) {
  return typeof v === 'number'
}
function isString(v: any) {
  return typeof v === 'string'
}
// 多行字符串（含换行的私钥等）用 textarea
function isMultiline(v: any) {
  return typeof v === 'string' && v.includes('\n')
}

function onStringInput(node: any, key: string, e: Event) {
  node[key] = (e.target as HTMLInputElement).value
}
function onNumberInput(node: any, key: string, e: Event) {
  const raw = (e.target as HTMLInputElement).value
  node[key] = raw === '' ? null : Number(raw)
}
function onBoolInput(node: any, key: string, e: Event) {
  node[key] = (e.target as HTMLInputElement).checked
}

function addArrayItem(node: any, key: string) {
  if (!Array.isArray(node[key])) node[key] = []
  // 根据现有元素类型给默认值
  const sample = node[key][0]
  if (typeof sample === 'object' && sample !== null) {
    node[key].push({ ...sample })
  } else {
    node[key].push('')
  }
}
function removeArrayItem(node: any, key: string, idx: number) {
  node[key].splice(idx, 1)
}

loadConfig()

// ========== AI 配置：主流模型预设 ==========
// 选预设 -> 自动填入 base_url / model，并聚焦 Key 输入框
const aiPresets = [
  { id: 'openai', label: 'OpenAI', base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini', keyPlaceholder: 'sk-...', needKey: true },
  { id: 'deepseek', label: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', keyPlaceholder: 'sk-...', needKey: true },
  { id: 'qwen', label: '通义千问', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus', keyPlaceholder: 'sk-...', needKey: true },
  { id: 'zhipu', label: '智谱 GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash', keyPlaceholder: '...', needKey: true },
  { id: 'ollama', label: '本地 Ollama', base_url: 'http://localhost:11434/v1', model: 'llama3.1', keyPlaceholder: '无需密钥，填 ollama 即可', needKey: false },
]

const aiActivePreset = ref<string>('')

function applyPreset(p: typeof aiPresets[number]) {
  if (!config.ai) config.ai = {}
  config.ai.base_url = p.base_url
  config.ai.model = p.model
  if (!p.needKey) {
    config.ai.api_key = 'ollama'
  } else if (!config.ai.api_key || config.ai.api_key === 'ollama') {
    config.ai.api_key = ''
  }
  aiActivePreset.value = p.id
}

// 依据当前 base_url 反推高亮哪个预设
function syncPresetHighlight() {
  const cur = config.ai?.base_url || ''
  const hit = aiPresets.find((p) => p.base_url === cur)
  aiActivePreset.value = hit ? hit.id : ''
}
</script>

<template>
  <div class="max-w-4xl mx-auto animate-fade-in">
    <!-- 页头 -->
    <div class="mb-6 flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <span>⚙️</span> 配置管理
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          加载并编辑本地 <code class="px-1 rounded bg-gray-100 dark:bg-gray-700">config.yaml</code>，保存后热重载生效
        </p>
      </div>
      <div class="flex gap-2">
        <button
          @click="loadConfig"
          :disabled="loading"
          class="px-4 py-2 rounded-xl text-sm font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors disabled:opacity-60"
        >
          {{ loading ? '加载中…' : '重新加载' }}
        </button>
        <button
          @click="saveConfig"
          :disabled="saving || !loaded"
          class="px-4 py-2 rounded-xl text-sm font-medium bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-60 shadow-sm"
        >
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
      </div>
    </div>

    <!-- 状态提示 -->
    <div v-if="error" class="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 text-sm">
      {{ error }}
    </div>
    <div v-if="message" class="mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-sm">
      {{ message }}
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="card p-10 text-center text-gray-400 text-sm animate-pulse">读取本地配置中…</div>

    <!-- 配置树（扁平化递归渲染） -->
    <div v-else-if="loaded" class="space-y-5">
      <template v-for="(value, key) in config" :key="key">
        <section class="card p-5">
          <h2 class="text-sm font-bold text-gray-800 dark:text-gray-100 mb-4 flex items-center gap-2">
            <span class="w-1.5 h-4 rounded-full bg-primary-500"></span>
            {{ key }}
          </h2>

          <!-- AI 专用：主流模型预设 + Key -->
          <div v-if="key === 'ai'" class="mb-5 space-y-3">
            <div>
              <p class="text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-2">主流模型（一键配置）</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="p in aiPresets"
                  :key="p.id"
                  @click="applyPreset(p)"
                  :class="[
                    'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                    aiActivePreset === p.id
                      ? 'bg-primary-500 text-white border-primary-500'
                      : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-300'
                  ]"
                >
                  {{ p.label }}
                </button>
              </div>
            </div>
            <p class="text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed">
              选预设后自动填充接口地址与默认模型，再在下方填入你的 Key 即可（Ollama 本地无需密钥）。
              也可在下方「自定义配置」中自由修改任意字段。
            </p>
          </div>

          <!-- 对象 -->
          <div v-if="isObject(value)" class="space-y-3 pl-2">
            <div v-for="(v, k) in value" :key="k" class="border-l-2 border-gray-100 dark:border-gray-700 pl-3">
              <label class="block text-[11px] font-medium text-gray-500 dark:text-gray-400 mb-1">{{ k }}</label>

              <!-- 嵌套对象 -->
              <div v-if="isObject(v)" class="space-y-2 pl-2">
                <div v-for="(vv, kk) in v" :key="kk">
                  <label class="block text-[10px] text-gray-400 mb-0.5">{{ kk }}</label>
                  <textarea v-if="isMultiline(vv)" :value="vv" @input="onStringInput(v, kk, $event)" rows="3" class="config-input font-mono text-xs"></textarea>
                  <input v-else-if="isNumber(vv)" type="number" :value="vv" @input="onNumberInput(v, kk, $event)" class="config-input" />
                  <input v-else-if="isBool(vv)" type="checkbox" :checked="vv" @change="onBoolInput(v, kk, $event)" class="w-4 h-4" />
                  <input v-else :value="vv" @input="onStringInput(v, kk, $event)" class="config-input" />
                </div>
              </div>

              <!-- 数组 -->
              <div v-else-if="isArray(v)" class="space-y-2">
                <div v-for="(item, idx) in v" :key="idx" class="border-l-2 border-gray-100 dark:border-gray-700 pl-3">
                  <!-- 数组元素为对象：递归渲染 -->
                  <div v-if="isObject(item)" class="space-y-2">
                    <div v-for="(vv, kk) in item" :key="kk">
                      <label class="block text-[10px] text-gray-400 mb-0.5">{{ kk }}</label>
                      <textarea v-if="isMultiline(vv)" :value="vv" @input="onStringInput(item, kk, $event)" rows="3" class="config-input font-mono text-xs"></textarea>
                      <input v-else-if="isNumber(vv)" type="number" :value="vv" @input="onNumberInput(item, kk, $event)" class="config-input" />
                      <input v-else-if="isBool(vv)" type="checkbox" :checked="vv" @change="onBoolInput(item, kk, $event)" class="w-4 h-4" />
                      <input v-else :value="vv" @input="onStringInput(item, kk, $event)" class="config-input" />
                    </div>
                    <button @click="removeArrayItem(value, k, idx)" class="text-[11px] text-red-600 dark:text-red-400 hover:underline">删除该项</button>
                  </div>
                  <!-- 数组元素为标量 -->
                  <div v-else class="flex items-center gap-2">
                    <input
                      :value="item"
                      @input="(e: any) => (v[idx] = e.target.value)"
                      class="config-input flex-1"
                    />
                    <button @click="removeArrayItem(value, k, idx)" class="w-7 h-7 flex-shrink-0 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-red-100 dark:hover:bg-red-500/20 hover:text-red-500 transition-colors">✕</button>
                  </div>
                </div>
                <button @click="addArrayItem(value, k)" class="text-[11px] text-primary-600 dark:text-primary-400 hover:underline">+ 添加一项</button>
              </div>

              <!-- 多行字符串 -->
              <textarea v-else-if="isMultiline(v)" :value="v" @input="onStringInput(value, k, $event)" rows="3" class="config-input font-mono text-xs"></textarea>
              <!-- 数字 -->
              <input v-else-if="isNumber(v)" type="number" :value="v" @input="onNumberInput(value, k, $event)" class="config-input" />
              <!-- 布尔 -->
              <label v-else-if="isBool(v)" class="flex items-center gap-2">
                <input type="checkbox" :checked="v" @change="onBoolInput(value, k, $event)" class="w-4 h-4" />
                <span class="text-xs text-gray-500 dark:text-gray-400">{{ v ? 'true' : 'false' }}</span>
              </label>
              <!-- 字符串 -->
              <input v-else :value="v" @input="onStringInput(value, k, $event)" class="config-input" />
            </div>
          </div>

          <!-- 顶层数组 -->
          <div v-else-if="isArray(value)" class="space-y-2">
            <div v-for="(item, idx) in value" :key="idx" class="flex items-center gap-2">
              <input :value="item" @input="(e: any) => (config[key][idx] = e.target.value)" class="config-input flex-1" />
              <button @click="removeArrayItem(config, key, idx)" class="w-7 h-7 flex-shrink-0 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-red-100 dark:hover:bg-red-500/20 hover:text-red-500 transition-colors">✕</button>
            </div>
            <button @click="addArrayItem(config, key)" class="text-[11px] text-primary-600 dark:text-primary-400 hover:underline">+ 添加一项</button>
          </div>

          <!-- 顶层标量 -->
          <div v-else>
            <textarea v-if="isMultiline(value)" :value="value" @input="onStringInput(config, key, $event)" rows="3" class="config-input font-mono text-xs"></textarea>
            <input v-else-if="isNumber(value)" type="number" :value="value" @input="onNumberInput(config, key, $event)" class="config-input" />
            <label v-else-if="isBool(value)" class="flex items-center gap-2">
              <input type="checkbox" :checked="value" @change="onBoolInput(config, key, $event)" class="w-4 h-4" />
              <span class="text-xs text-gray-500 dark:text-gray-400">{{ value ? 'true' : 'false' }}</span>
            </label>
            <input v-else :value="value" @input="onStringInput(config, key, $event)" class="config-input" />
          </div>
        </section>
      </template>

      <p class="text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed">
        提示：修改 <code>datasource</code>（天气/新闻/周边/AI）等运行期配置保存后即生效；
        <code>server</code> 端口、<code>app</code> 名称等启动期配置需重启后端进程才能完全生效。
        保存会覆盖原文件并丢失注释。
      </p>
    </div>
  </div>
</template>

<style scoped>
.config-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
  border-radius: 0.5rem;
  background: white;
  border: 1px solid rgb(229 231 235);
  color: rgb(31 41 55);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
:global(.dark) .config-input {
  background: rgb(31 41 55);
  border-color: rgb(55 65 81);
  color: rgb(229 231 235);
}
.config-input:focus {
  border-color: rgb(99 102 241);
  box-shadow: 0 0 0 3px rgb(99 102 241 / 0.15);
}
</style>
