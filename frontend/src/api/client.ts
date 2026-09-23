export type ArticleStatus = 'ingested' | 'approved' | 'rejected' | 'published'

export interface Article {
  id: string
  source_id: string | null
  title: string
  summary: string
  body_html: string
  source_url: string
  author: string
  status: ArticleStatus
  quality_score: number
  topics: string
  metrics: string
}

export interface Draft {
  title: string
  summary: string
  body_html: string
  source_url: string
  author: string
}

function errorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object' || !('detail' in body)) return fallback
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String(item.msg)
        return ''
      })
      .filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return fallback
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(errorDetail(body, '请求失败'))
  }
  return res.json() as Promise<T>
}

export interface Health {
  status: string
  wechat_configured: boolean
  llm_configured: boolean
  auto_publish: boolean
}

export const api = {
  health: () => fetch('/api/v1/health').then((r) => parse<Health>(r)),
  fetchDraft: (payload: { title: string; source_url: string; author?: string }) =>
    fetch('/api/v1/draft/fetch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<Draft>(r)),
  polishDraft: (payload: Draft & { style: string }) =>
    fetch('/api/v1/draft/polish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<Draft>(r)),
  publishDraft: (payload: Draft) =>
    fetch('/api/v1/draft/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<{ message: string }>(r)),
  listArticles: () => fetch('/api/v1/articles').then((r) => parse<Article[]>(r)),
  createManual: (payload: { title: string; source_url: string; author?: string }) =>
    fetch('/api/v1/articles/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<Article>(r)),
  updateArticle: (id: string, payload: Partial<Article>) =>
    fetch(`/api/v1/articles/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<Article>(r)),
  approve: (id: string) =>
    fetch(`/api/v1/articles/${id}/approve`, { method: 'POST' }).then((r) => parse<Article>(r)),
  polish: (id: string, style: string) =>
    fetch(`/api/v1/articles/${id}/polish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style }),
    }).then((r) => parse<Article>(r)),
  publish: (id: string) =>
    fetch(`/api/v1/articles/${id}/publish`, { method: 'POST' }).then((r) =>
      parse<{ message: string }>(r),
    ),
}
