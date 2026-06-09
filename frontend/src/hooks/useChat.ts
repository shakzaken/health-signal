import { useState, useCallback } from 'react'
import type { Message, SourceChunk, Session } from '../types'
import { sendQueryStream } from '../api/backend'

const SESSIONS_KEY = 'hs_sessions'
const ACTIVE_SESSION_KEY = 'hs_active_session'

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Session[]
    // Restore Date objects
    return parsed.map((s) => ({ ...s, createdAt: new Date(s.createdAt) }))
  } catch {
    return []
  }
}

function saveSessions(sessions: Session[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
  } catch {
    // ignore quota errors
  }
}

function saveActiveSession(session: Session | null) {
  try {
    if (session) {
      localStorage.setItem(ACTIVE_SESSION_KEY, JSON.stringify(session))
    } else {
      localStorage.removeItem(ACTIVE_SESSION_KEY)
    }
  } catch {
    // ignore quota errors
  }
}

function loadActiveSession(): Session | null {
  try {
    const raw = localStorage.getItem(ACTIVE_SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Session
    return { ...parsed, createdAt: new Date(parsed.createdAt) }
  } catch {
    return null
  }
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>(() => loadActiveSession()?.messages ?? [])
  const [sessionId, setSessionId] = useState<string>(() => loadActiveSession()?.id ?? crypto.randomUUID())
  const [isLoading, setIsLoading] = useState(false)
  const [sources, setSources] = useState<SourceChunk[]>(() => loadActiveSession()?.sources ?? [])
  const [error, setError] = useState<string | null>(null)
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions())

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return

    const userMessage: Message = { role: 'user', content: text }
    const messagesWithUser = [...messages, userMessage]
    setMessages(messagesWithUser)
    setIsLoading(true)
    setError(null)
    setSources([])

    let streamedContent = ''
    let finalSources: SourceChunk[] = []

    try {
      for await (const event of sendQueryStream(text, sessionId)) {
        if (event.token !== undefined) {
          streamedContent += event.token
          // Show partial message with streaming cursor in real-time
          setMessages([
            ...messagesWithUser,
            { role: 'assistant', content: streamedContent, streaming: true },
          ])
        } else if (event.sources !== undefined) {
          finalSources = event.sources
        }
      }

      // Stream complete — finalize (remove streaming flag)
      const assistantMessage: Message = { role: 'assistant', content: streamedContent }
      const finalMessages = [...messagesWithUser, assistantMessage]
      setMessages(finalMessages)
      setSources(finalSources)

      // Upsert this session in the sidebar
      const firstUserMsg = finalMessages.find((m) => m.role === 'user')
      const title = firstUserMsg
        ? firstUserMsg.content.slice(0, 60) + (firstUserMsg.content.length > 60 ? '…' : '')
        : 'Conversation'
      const upserted: Session = {
        id: sessionId,
        title,
        messages: finalMessages,
        sources: finalSources,
        createdAt: new Date(),
      }
      setSessions((prev) => {
        const exists = prev.some((s) => s.id === sessionId)
        const updated = exists
          ? prev.map((s) => (s.id === sessionId ? upserted : s))
          : [upserted, ...prev]
        saveSessions(updated)
        return updated
      })

      // Persist active session so it survives page refresh
      saveActiveSession(upserted)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
      // Remove user message if we got nothing back
      if (!streamedContent) {
        setMessages((prev) => prev.slice(0, -1))
      } else {
        // Keep partial content without streaming flag
        setMessages([
          ...messagesWithUser,
          { role: 'assistant', content: streamedContent },
        ])
      }
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId, messages])

  const newConversation = useCallback(() => {
    // Session is already upserted in the sidebar after each response — just reset active state
    saveActiveSession(null)
    setMessages([])
    setSources([])
    setError(null)
    setSessionId(crypto.randomUUID())
  }, [])

  const restoreSession = useCallback((session: Session) => {
    // Restore session as the active conversation; keep it in the sidebar history
    setMessages(session.messages)
    setSources(session.sources)
    setSessionId(session.id)
    setError(null)
    saveActiveSession(session)
  }, [])

  return { messages, sessionId, isLoading, sources, error, sessions, sendMessage, newConversation, restoreSession }
}
