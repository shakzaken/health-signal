export interface DocumentResponse {
  id: string
  filename: string
  document_type: string
  processing_status: string
  uploaded_at: string
}

export interface SourceChunk {
  filename: string
  document_type: string
  source_date: string | null
  score: number
  text: string
}

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
}

export interface ReportResponse {
  report: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface Session {
  id: string
  title: string       // first user message (truncated)
  messages: Message[]
  sources: SourceChunk[]
  createdAt: Date
}
