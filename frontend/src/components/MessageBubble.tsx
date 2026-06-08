import type { Message } from '../types'
import { PulseIcon } from './Icons'

interface MessageBubbleProps {
  message: Message
}

function AssistantAvatar() {
  return (
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
  )
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div style={{ alignSelf: 'flex-end', maxWidth: '74%' }}>
        <div
          style={{
            background: 'var(--accent)',
            color: '#fff',
            padding: '11px 15px',
            borderRadius: 'var(--radius) var(--radius) calc(var(--radius) * 0.3) var(--radius)',
            fontSize: 14.5,
            lineHeight: 1.5,
            boxShadow: '0 1px 2px rgba(45,85,60,.22)',
            whiteSpace: 'pre-wrap',
          }}
        >
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div
      style={{
        alignSelf: 'flex-start',
        maxWidth: '88%',
        display: 'flex',
        gap: 11,
      }}
    >
      <AssistantAvatar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            padding: '14px 16px',
            borderRadius: 'calc(var(--radius) * 0.3) var(--radius) var(--radius) var(--radius)',
            fontSize: 14.5,
            lineHeight: 1.62,
            color: '#27313F',
            boxShadow: '0 1px 2px rgba(20,30,50,.04)',
            whiteSpace: 'pre-wrap',
          }}
        >
          {message.content}
          {message.streaming && (
            <span
              style={{
                display: 'inline-block',
                width: 2,
                height: '1em',
                background: 'var(--accent)',
                marginLeft: 2,
                verticalAlign: 'text-bottom',
                animation: 'hsblink 0.8s step-end infinite',
              }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
