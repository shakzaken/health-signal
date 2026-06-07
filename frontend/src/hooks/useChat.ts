import { useState, useCallback } from 'react'
import type { Message, SourceChunk } from '../types'
import { sendQuery } from '../api/aiAgent'

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID())
  const [isLoading, setIsLoading] = useState(false)
  const [sources, setSources] = useState<SourceChunk[]>([])
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (text: string, documentType?: string) => {
    if (!text.trim() || isLoading) return

    const userMessage: Message = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)
    setError(null)
    setSources([])

    try {
      const result = await sendQuery(text, sessionId, documentType)
      const assistantMessage: Message = { role: 'assistant', content: result.answer }
      setMessages((prev) => [...prev, assistantMessage])
      setSources(result.sources)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
      // Remove the user message so they can retry
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId])

  const newConversation = useCallback(() => {
    setMessages([])
    setSources([])
    setError(null)
    setSessionId(crypto.randomUUID())
  }, [])

  return { messages, sessionId, isLoading, sources, error, sendMessage, newConversation }
}
