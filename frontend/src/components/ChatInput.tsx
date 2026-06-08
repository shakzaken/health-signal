import { useRef, type KeyboardEvent } from 'react'
import { SendIcon } from './Icons'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ value, onChange, onSend, disabled }: ChatInputProps) {
  const taRef = useRef<HTMLTextAreaElement>(null)

  function handleSend() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    // Reset textarea height
    if (taRef.current) taRef.current.style.height = 'auto'
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = value.trim().length > 0 && !disabled

  return (
    <div
      style={{
        flexShrink: 0,
        padding: '12px 0 18px',
        background: 'linear-gradient(180deg, transparent, var(--bg) 36%)',
      }}
    >
      <div style={{ maxWidth: 740, margin: '0 auto', padding: '0 28px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 10,
            background: 'var(--surface)',
            border: `1px solid ${canSend ? 'var(--accent)' : 'var(--border-strong)'}`,
            borderRadius: 'var(--radius)',
            padding: '8px 8px 8px 16px',
            boxShadow: canSend
              ? '0 0 0 3px var(--accent-soft), 0 2px 12px rgba(20,30,50,.06)'
              : '0 2px 12px rgba(20,30,50,.06)',
            transition: 'border-color .15s, box-shadow .15s',
          }}
        >
          <textarea
            ref={taRef}
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              // Auto-resize
              e.target.style.height = 'auto'
              e.target.style.height = `${e.target.scrollHeight}px`
            }}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder="Ask about your health data…"
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              resize: 'none',
              background: 'transparent',
              fontFamily: 'inherit',
              fontSize: 14.5,
              color: 'var(--ink)',
              padding: '9px 0',
              lineHeight: 1.4,
              maxHeight: 120,
              overflowY: 'auto',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            style={{
              border: 'none',
              background: canSend ? 'var(--accent)' : 'var(--border-strong)',
              color: '#fff',
              fontWeight: 500,
              fontSize: 13.5,
              padding: '0 18px',
              height: 40,
              borderRadius: 'calc(var(--radius) * 0.7)',
              cursor: canSend ? 'pointer' : 'default',
              fontFamily: 'inherit',
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              transition: 'background .15s',
              flexShrink: 0,
            }}
          >
            Send
            <SendIcon size={15} color="#fff" />
          </button>
        </div>
        <div
          style={{
            fontSize: 11,
            color: 'var(--faint)',
            textAlign: 'center',
            marginTop: 9,
          }}
        >
          HealthSignal can make mistakes and is not a substitute for professional medical advice.
        </div>
      </div>
    </div>
  )
}
