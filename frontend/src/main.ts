import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(router)

// 全局点击水波纹遮罩：自动作用于页面上所有 <button>，无需逐个组件接入
function createRipple(e: PointerEvent) {
  const target = (e.target as HTMLElement | null)?.closest('button')
  if (!target) return
  const el = target as HTMLElement
  const rect = el.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height)
  // 确保按钮能容纳并裁剪水波纹
  const cs = getComputedStyle(el)
  if (cs.position === 'static') el.style.position = 'relative'
  el.style.overflow = 'hidden'
  el.style.isolation = 'isolate'

  const span = document.createElement('span')
  span.className = 'ripple-mask'
  span.style.width = span.style.height = `${size}px`
  span.style.left = `${e.clientX - rect.left - size / 2}px`
  span.style.top = `${e.clientY - rect.top - size / 2}px`
  span.addEventListener('animationend', () => span.remove())
  el.appendChild(span)
}
document.addEventListener('pointerdown', createRipple)

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
