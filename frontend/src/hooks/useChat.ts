import { useState, useCallback, useEffect } from 'react'
import type { Message, SourceChunk, Session } from '../types'
import { sendQueryStream, listConversations, fetchConversationMessages } from '../api/backend'

function activeSessionKey(userEmail: string) { return `hs_active_session_${userEmail}` }

function saveActiveSession(userEmail: string, session: Session | null) {
  try {
    if (session) {
      localStorage.setItem(activeSessionKey(userEmail), JSON.stringify(session))
    } else {
      localStorage.removeItem(activeSessionKey(userEmail))
    }
  } catch {
    // ignore quota errors
  }
}

function loadActiveSession(userEmail: string): Session | null {
  try {
    const raw = localStorage.getItem(activeSessionKey(userEmail))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Session
    return { ...parsed, createdAt: new Date(parsed.createdAt) }
  } catch {
    return null
  }
}

export function useChat(userEmail: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID())
  const [isLoading, setIsLoading] = useState(false)
  const [sources, setSources] = useState<SourceChunk[]>([])
  const [error, setError] = useState<string | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])

  // Reset all chat state whenever the active user changes (login/logout/account
  // switch) — without this, switching accounts within the same SPA session
  // leaves the previous user's messages visible in the chat pane, since this
  // hook instance stays mounted across login/logout instead of remounting.
  useEffect(() => {
    if (!userEmail) {
      setMessages([])
      setSources([])
      setSessions([])
      setSessionId(crypto.randomUUID())
      setError(null)
      return
    }

    const active = loadActiveSession(userEmail)
    setMessages(active?.messages ?? [])
    setSources(active?.sources ?? [])
    setSessionId(active?.id ?? crypto.randomUUID())
    setError(null)

    listConversations()
      .then((items) => {
        setSessions(items.map((item) => ({
          id: item.session_id,
          title: item.title,
          messages: [],
          sources: [],
          createdAt: new Date(item.updated_at),
        })))
      })
      .catch(() => {
        // Non-fatal — sidebar just stays empty
      })
  }, [userEmail])

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
          setMessages([
            ...messagesWithUser,
            { role: 'assistant', content: streamedContent, streaming: true },
          ])
        } else if (event.sources !== undefined) {
          finalSources = event.sources
        }
      }

      const assistantMessage: Message = { role: 'assistant', content: streamedContent }
      const finalMessages = [...messagesWithUser, assistantMessage]
      setMessages(finalMessages)
      setSources(finalSources)

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

      // Update sidebar — upsert this session
      setSessions((prev) => {
        const exists = prev.some((s) => s.id === sessionId)
        return exists
          ? prev.map((s) => (s.id === sessionId ? upserted : s))
          : [upserted, ...prev]
      })

      saveActiveSession(userEmail, upserted)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
      if (!streamedContent) {
        setMessages((prev) => prev.slice(0, -1))
      } else {
        setMessages([
          ...messagesWithUser,
          { role: 'assistant', content: streamedContent },
        ])
      }
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId, messages, userEmail])

  const newConversation = useCallback(() => {
    saveActiveSession(userEmail, null)
    setMessages([])
    setSources([])
    setError(null)
    setSessionId(crypto.randomUUID())
  }, [userEmail])

  const restoreSession = useCallback(async (session: Session) => {
    // If messages are already loaded (current session), restore directly
    if (session.messages.length > 0) {
      setMessages(session.messages)
      setSources(session.sources)
      setSessionId(session.id)
      setError(null)
      saveActiveSession(userEmail, session)
      return
    }

    // Fetch messages from server for sessions loaded from server list
    try {
      const data = await fetchConversationMessages(session.id)
      const restored: Session = {
        ...session,
        messages: data.messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })),
      }
      setMessages(restored.messages)
      setSources(restored.sources)
      setSessionId(restored.id)
      setError(null)
      saveActiveSession(userEmail, restored)
    } catch {
      // Fallback — open empty session with same id
      setMessages([])
      setSources([])
      setSessionId(session.id)
      setError(null)
    }
  }, [userEmail])

  return { messages, sessionId, isLoading, sources, error, sessions, sendMessage, newConversation, restoreSession }
}
