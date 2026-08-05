<script setup lang="ts">
const props = defineProps<{ modelValue: any }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: any): void }>()

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
function isMultiline(v: any) {
  return typeof v === 'string' && v.includes('\n')
}

function updateVal(next: any) {
  emit('update:modelValue', next)
}

function updateKey(obj: any, key: string, val: any) {
  const next = { ...obj, [key]: val }
  updateVal(next)
}

function onStringInput(e: Event) {
  updateVal((e.target as HTMLInputElement).value)
}
function onNumberInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value
  updateVal(raw === '' ? null : Number(raw))
}
function onBoolInput(e: Event) {
  updateVal((e.target as HTMLInputElement).checked)
}

function addArrayItem(arr: any[]) {
  const sample = arr[0]
  let item: any
  if (typeof sample === 'object' && sample !== null) {
    item = Array.isArray(sample) ? [...sample] : { ...sample }
  } else {
    item = ''
  }
  updateVal([...arr, item])
}
function removeArrayItem(arr: any[], idx: number) {
  const next = [...arr]
  next.splice(idx, 1)
  updateVal(next)
}
function updateArrayItem(arr: any[], idx: number, val: any) {
  const next = [...arr]
  next[idx] = val
  updateVal(next)
}
</script>

<template>
  <!-- 对象：递归渲染每个 key -->
  <div v-if="isObject(modelValue)" class="space-y-3 pl-2">
    <div
      v-for="(v, k) in modelValue"
      :key="k"
      class="border-l-2 border-gray-100 dark:border-gray-700 pl-3"
    >
      <label class="block text-[11px] font-medium text-gray-500 dark:text-gray-400 mb-1">{{ k }}</label>
      <ConfigEditor
        :model-value="v"
        @update:model-value="(val) => updateKey(modelValue, k as string, val)"
      />
    </div>
  </div>

  <!-- 数组：递归渲染每个元素 -->
  <div v-else-if="isArray(modelValue)" class="space-y-2">
    <div
      v-for="(item, idx) in modelValue"
      :key="idx"
      class="border-l-2 border-gray-100 dark:border-gray-700 pl-3"
    >
      <div class="flex items-start gap-2">
        <ConfigEditor
          :model-value="item"
          @update:model-value="(val) => updateArrayItem(modelValue, idx, val)"
          class="flex-1"
        />
        <button
          @click="removeArrayItem(modelValue, idx)"
          class="mt-1 w-7 h-7 flex-shrink-0 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-red-100 dark:hover:bg-red-500/20 hover:text-red-500 transition-colors"
        >✕</button>
      </div>
    </div>
    <button
      @click="addArrayItem(modelValue)"
      class="text-[11px] text-primary-600 dark:text-primary-400 hover:underline"
    >+ 添加一项</button>
  </div>

  <!-- 标量 -->
  <div v-else>
    <textarea
      v-if="isMultiline(modelValue)"
      :value="modelValue"
      @input="onStringInput"
      rows="3"
      class="config-input font-mono text-xs"
    ></textarea>
    <input
      v-else-if="isNumber(modelValue)"
      type="number"
      :value="modelValue"
      @input="onNumberInput"
      class="config-input"
    />
    <label v-else-if="isBool(modelValue)" class="flex items-center gap-2">
      <input type="checkbox" :checked="modelValue" @change="onBoolInput" class="w-4 h-4" />
      <span class="text-xs text-gray-500 dark:text-gray-400">{{ modelValue ? 'true' : 'false' }}</span>
    </label>
    <input
      v-else
      :value="modelValue"
      @input="onStringInput"
      class="config-input"
    />
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
