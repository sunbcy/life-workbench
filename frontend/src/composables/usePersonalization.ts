import { ref } from 'vue'

const STORAGE_KEY = 'life-workbench:personalization-enabled'

const enabled = ref(true)
let initialized = false

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw !== null) {
      enabled.value = raw === 'true'
    }
  } catch {
    // ignore storage errors
  }
}

function save(value: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, String(value))
  } catch {
    // ignore storage errors
  }
}

export function usePersonalization() {
  if (typeof window !== 'undefined' && !initialized) {
    load()
    initialized = true
  }

  function toggle() {
    enabled.value = !enabled.value
    save(enabled.value)
  }

  function set(value: boolean) {
    enabled.value = value
    save(value)
  }

  return { enabled, toggle, set }
}
