import type { DocumentResponse, SourceChunk } from '../types'

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'
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

export interface DocumentUploadResponse {
  id: string
  filename: string
  document_type: string
  processing_status: string
  source_date: string | null
  uploaded_at: string
}

export async function uploadDocument(
  file: File,
  sourceDate?: string,
): Promise<DocumentUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  if (sourceDate) {
    form.append('source_date', sourceDate)
  }
  return request<DocumentUploadResponse>('/documents/upload', {
    method: 'POST',
    body: form,
  })
}

export async function getDocumentStatus(id: string): Promise<DocumentResponse> {
  return request<DocumentResponse>(`/documents/${id}`)
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  return request<DocumentResponse[]>('/documents')
}

// ── AI agent (proxied through backend) ────────────────────────────────────

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
}

export interface ReportResponse {
  report: string
}

export type StreamEvent =
  | { token: string; sources?: never }
  | { sources: SourceChunk[]; token?: never }

export async function sendQuery(
  question: string,
  sessionId: string,
): Promise<QueryResponse> {
  return request<QueryResponse>('/ai/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
  })
}

export async function* sendQueryStream(
  question: string,
  sessionId: string,
): AsyncGenerator<StreamEvent> {
  const token = getToken()
  const res = await fetch(`${BASE_URL}/ai/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, session_id: sessionId }),
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
  return request<ReportResponse>('/ai/report/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ period_days: periodDays }),
  })
}

export interface ConversationListItem {
  session_id: string
  title: string
  updated_at: string
}

export interface ConversationMessagesResponse {
  messages: { role: string; content: string }[]
}

export async function listConversations(): Promise<ConversationListItem[]> {
  return request<ConversationListItem[]>('/conversations')
}

export async function fetchConversationMessages(sessionId: string): Promise<ConversationMessagesResponse> {
  return request<ConversationMessagesResponse>(`/conversations/${sessionId}?recent=200`)
}
