import { ref, type Ref } from 'vue'

// 后端日志开关：控制后端是否打印详细请求/业务日志。
// 前端只暴露“开 / 关”两态；开 -> 后端 INFO（打印每个接口一行日志 + 业务 info），
// 关 -> 后端 WARNING（仅错误）。状态持久化到 localStorage，并实时同步给后端。
const STORAGE_KEY = 'backend_log_enabled'

const enabled: Ref<boolean> = ref(localStorage.getItem(STORAGE_KEY) === '1')

async function pushToBackend(on: boolean) {
  try {
    await fetch('/api/logs/level', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level: on ? 'INFO' : 'WARNING' }),
    })
  } catch {
    // 后端不可用时静默，开关状态仍保存在本地
  }
}

// 初始化：把本地状态同步给后端（开/关）
pushToBackend(enabled.value)

async function toggle() {
  enabled.value = !enabled.value
  localStorage.setItem(STORAGE_KEY, enabled.value ? '1' : '0')
  await pushToBackend(enabled.value)
  return enabled.value
}

export function useLogToggle() {
  return { enabled, toggle }
}
