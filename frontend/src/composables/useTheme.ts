import { ref, watchEffect } from 'vue'

const isDark = ref(false)

export function useTheme() {
  // 初始化：检查系统偏好或本地存储
  const stored = localStorage.getItem('theme')
  if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDark.value = true
  }

  watchEffect(() => {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  })

  function toggle() {
    isDark.value = !isDark.value
  }

  return { isDark, toggle }
}
