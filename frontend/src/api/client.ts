export type ArticleStatus = 'ingested' | 'approved' | 'rejected' | 'published'

export interface Source {
  id: string
  name: string
  url: string
  kind: string
  enabled: boolean
  topics: string
}

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
}

export interface Health {
  status: string
  wechat_configured: boolean
  llm_configured: boolean
  auto_publish: boolean
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((body as { detail?: string }).detail || '请求失败')
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => fetch('/api/v1/health').then((r) => parse<Health>(r)),
  listSources: () => fetch('/api/v1/sources').then((r) => parse<Source[]>(r)),
  createSource: (payload: { name: string; url: string; topics: string }) =>
    fetch('/api/v1/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<Source>(r)),
  deleteSource: (id: string) =>
    fetch(`/api/v1/sources/${id}`, { method: 'DELETE' }).then((r) => parse<{ message: string }>(r)),
  ingest: () =>
    fetch('/api/v1/sources/ingest', { method: 'POST' }).then((r) =>
      parse<{ message: string; created: number; skipped: number }>(r),
    ),
  listArticles: (status?: ArticleStatus) => {
    const q = status ? `?status=${status}` : ''
    return fetch(`/api/v1/articles${q}`).then((r) => parse<Article[]>(r))
  },
  updateArticle: (id: string, payload: Partial<Article>) =>
    fetch(`/api/v1/articles/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => parse<Article>(r)),
  approve: (id: string) =>
    fetch(`/api/v1/articles/${id}/approve`, { method: 'POST' }).then((r) => parse<Article>(r)),
  reject: (id: string) =>
    fetch(`/api/v1/articles/${id}/reject`, { method: 'POST' }).then((r) => parse<Article>(r)),
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
