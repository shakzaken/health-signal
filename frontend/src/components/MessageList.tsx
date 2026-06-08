import { useEffect, useRef } from 'react'
import type { Message, SourceChunk } from '../types'
import MessageBubble from './MessageBubble'
import SourcePanel from './SourcePanel'
import { PulseIcon } from './Icons'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
  sources: SourceChunk[]
  onSelectPrompt: (prompt: string) => void
}

function TypingDots() {
  return (
    <div style={{ alignSelf: 'flex-start', maxWidth: '88%', display: 'flex', gap: 11 }}>
      <div
        style={{
          flexShrink: 0,
          width: 30,
          height: 30,
          borderRadius: 9,
          background: 'var(--accent-soft)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginTop: 1,
        }}
      >
        <PulseIcon size={16} color="var(--accent)" sw={2} />
      </div>
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          padding: '14px 16px',
          borderRadius: 'calc(var(--radius) * 0.3) var(--radius) var(--radius) var(--radius)',
          boxShadow: '0 1px 2px rgba(20,30,50,.04)',
        }}
      >
        <div style={{ display: 'flex', gap: 4, padding: '4px 2px' }}>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: 'var(--faint)',
                animation: `hsbounce 1.2s ${i * 0.15}s infinite ease-in-out`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

const STARTER_PROMPTS = [
  'Do my recent labs show anything I should watch?',
  'How have my key markers changed over time?',
  'Summarize my recent symptoms',
  'What supplements am I currently taking?',
]

export default function MessageList({ messages, isLoading, sources, onSelectPrompt }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const hasMessages = messages.length > 0
  const lastMessage = messages[messages.length - 1]
  const showSources = sources.length > 0 && !isLoading && lastMessage?.role === 'assistant'

  return (
    <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
      <div
        style={{
          maxWidth: 740,
          margin: '0 auto',
          padding: '24px 28px 8px',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        {/* Date pill */}
        <div
          style={{
            alignSelf: 'center',
            fontSize: 11.5,
            color: 'var(--faint)',
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            padding: '4px 12px',
            borderRadius: 20,
          }}
        >
          Today · grounded in your documents
        </div>

        {/* Messages */}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* Sources (inline after last assistant message) */}
        {showSources && <SourcePanel sources={sources} />}

        {/* Loading indicator */}
        {isLoading && <TypingDots />}

        {/* Starter prompts — shown when no messages yet */}
        {!hasMessages && !isLoading && (
          <div style={{ marginTop: 6, marginLeft: 41 }}>
            <div
              style={{
                fontSize: 11.5,
                fontWeight: 600,
                letterSpacing: '.05em',
                textTransform: 'uppercase',
                color: 'var(--faint)',
                marginBottom: 9,
              }}
            >
              Try asking
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {STARTER_PROMPTS.map((p, i) => (
                <button
                  key={i}
                  onClick={() => onSelectPrompt(p)}
                  style={{
                    textAlign: 'left',
                    padding: '9px 13px',
                    borderRadius: 'calc(var(--radius) * 0.8)',
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    fontSize: 13,
                    color: 'var(--sub)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    maxWidth: 330,
                    lineHeight: 1.4,
                    transition: 'border-color .12s, color .12s, background .12s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent)'
                    e.currentTarget.style.color = 'var(--ink)'
                    e.currentTarget.style.background = 'var(--accent-soft)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border)'
                    e.currentTarget.style.color = 'var(--sub)'
                    e.currentTarget.style.background = 'var(--surface)'
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
