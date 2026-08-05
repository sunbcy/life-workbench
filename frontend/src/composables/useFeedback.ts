import type { NewsArticle } from '@/types'

/**
 * 隐式反馈埋点
 *
 * 设计原则：埋点是旁路，任何失败都必须静默，绝不影响主流程。
 */

export type FeedbackAction =
  | 'impression'
  | 'click'
  | 'dwell'
  | 'open_link'
  | 'like'
  | 'not_interested'

/** 低于此停留时长视为误点，不上报 dwell */
const MIN_DWELL_MS = 3000

export interface FeedbackPayload {
  article_id: string
  action: FeedbackAction
  dwell_ms?: number
  tags?: string[]
  category?: string
  title?: string
}

async function post(payload: FeedbackPayload): Promise<void> {
  try {
    await fetch('/api/news/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true, // 页面卸载时仍能发出
    })
  } catch {
    // 静默失败：埋点不应干扰用户
  }
}

export function useFeedback() {
  /** 通用上报 */
  function report(article: NewsArticle, action: FeedbackAction, dwellMs = 0) {
    if (!article) return
    void post({
      article_id: String(article.id),
      action,
      dwell_ms: Math.round(dwellMs),
      tags: article.tags || [],
      category: article.category || '',
      title: article.title || '',
    })
  }

  /** 点开详情 */
  function reportClick(article: NewsArticle) {
    report(article, 'click')
  }

  /** 关闭详情时上报停留时长（过短视为误点，丢弃） */
  function reportDwell(article: NewsArticle, dwellMs: number) {
    if (dwellMs < MIN_DWELL_MS) return
    report(article, 'dwell', dwellMs)
  }

  /** 跳转原文 —— 最强正向信号 */
  function reportOpenLink(article: NewsArticle) {
    report(article, 'open_link')
  }

  /** 显式负反馈 */
  function reportNotInterested(article: NewsArticle) {
    report(article, 'not_interested')
  }

  return {
    report,
    reportClick,
    reportDwell,
    reportOpenLink,
    reportNotInterested,
    MIN_DWELL_MS,
  }
}
