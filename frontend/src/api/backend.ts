import type { DocumentResponse } from '../types'

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
