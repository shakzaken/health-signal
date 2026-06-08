import type { QueryResponse, ReportResponse, SourceChunk } from '../types'

const BASE_URL = import.meta.env.VITE_AI_AGENT_URL ?? 'http://localhost:8001'
const TOKEN_KEY = 'hs_token'

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  })
  if (res.status === 401) {
    // Token expired or invalid — clear it and reload to login page
    localStorage.removeItem(TOKEN_KEY)
    window.location.reload()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function sendQuery(
  question: string,
  sessionId: string,
  documentType?: string,
): Promise<QueryResponse> {
  return request<QueryResponse>('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      document_type: documentType ?? null,
    }),
  })
}

export type StreamEvent =
  | { token: string; sources?: never }
  | { sources: SourceChunk[]; token?: never }

export async function* sendQueryStream(
  question: string,
  sessionId: string,
  documentType?: string,
): AsyncGenerator<StreamEvent> {
  const token = getToken()
  const res = await fetch(`${BASE_URL}/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      document_type: documentType ?? null,
    }),
  })

  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY)
    window.location.reload()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data) {
          try {
            yield JSON.parse(data) as StreamEvent
          } catch {
            // ignore malformed events
          }
        }
      }
    }
  }
}

export async function generateReport(periodDays: number): Promise<ReportResponse> {
  return request<ReportResponse>('/report/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ period_days: periodDays }),
  })
}
