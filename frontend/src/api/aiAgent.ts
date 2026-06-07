import type { QueryResponse, ReportResponse } from '../types'

const BASE_URL = import.meta.env.VITE_AI_AGENT_URL ?? 'http://localhost:8001'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
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

export async function generateReport(periodDays: number): Promise<ReportResponse> {
  return request<ReportResponse>('/report/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ period_days: periodDays }),
  })
}
