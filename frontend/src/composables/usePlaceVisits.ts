/**
 * 到店记录 — 用户对周边资源卡片的自标注（去过/没去过/好吃不好吃）
 *
 * 设计原则：与新闻隐式反馈隔离，独立后端存储；任何失败静默，绝不干扰主流程。
 */

const BASE = '/api'

export type VisitAction = 'visited' | 'not_visited' | 'experience'

export interface VisitRecord {
  resource_id: string | number
  resource_name?: string
  action: VisitAction
  taste?: 'good' | 'bad'
  note?: string
}

async function postVisit(rec: VisitRecord): Promise<void> {
  try {
    await fetch(`${BASE}/nearby/visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resource_id: String(rec.resource_id),
        resource_name: rec.resource_name || '',
        action: rec.action,
        taste: rec.taste || '',
        note: rec.note || '',
      }),
    })
  } catch {
    // 静默失败
  }
}

async function fetchSummary(resources: { id: number | string }[]): Promise<Record<string, any>> {
  const ids = resources.map((r) => String(r.id)).join(',')
  if (!ids) return {}
  try {
    const resp = await fetch(`${BASE}/nearby/visit/summary?ids=${encodeURIComponent(ids)}`)
    const json = await resp.json()
    if (json.code === 0) return json.data || {}
  } catch {
    // 静默降级：卡片不显示自标注信息
  }
  return {}
}

/** 把后端 summary 注入到资源列表的 visit_info 字段 */
export function applyVisitInfo(
  resources: { id: number | string; visit_info?: any }[],
  summary: Record<string, any>,
): void {
  for (const r of resources) {
    const info = summary[String(r.id)]
    if (info) r.visit_info = info
  }
}

export function usePlaceVisits() {
  return { postVisit, fetchSummary, applyVisitInfo }
}
