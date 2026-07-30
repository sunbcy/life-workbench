import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(router)

// 全局错误捕获 — 防止模板渲染错误导致白屏
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', err)
  console.error('  Component:', instance?.$options?.name || instance?.$.type?.name || 'unknown')
  console.error('  Info:', info)
  // 在 DOM 中显示错误提示（仅开发模式）
  const appEl = document.getElementById('app')
  if (appEl && !appEl.querySelector('.vue-error-toast')) {
    const toast = document.createElement('div')
    toast.className = 'vue-error-toast'
    toast.style.cssText = 'position:fixed;bottom:16px;left:16px;right:16px;z-index:9999;padding:12px 16px;background:#fef2f2;border:1px solid #fecaca;border-radius:12px;font-size:12px;color:#dc2626;font-family:sans-serif;max-height:120px;overflow-y:auto;'
    toast.textContent = `⚠️ 页面渲染错误: ${(err as Error)?.message || String(err)}`
    appEl.appendChild(toast)
    setTimeout(() => toast.remove(), 8000)
  }
}

app.mount('#app')
