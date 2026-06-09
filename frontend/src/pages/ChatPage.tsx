import { useState } from 'react'
import type { useChat } from '../hooks/useChat'
import MessageList from '../components/MessageList'
import ChatInput from '../components/ChatInput'
import { PlusIcon } from '../components/Icons'

type ChatState = ReturnType<typeof useChat>

interface ChatPageProps {
  chatState: ChatState
}

export default function ChatPage({ chatState }: ChatPageProps) {
  const { messages, isLoading, sources, error, sendMessage, newConversation } = chatState
  const [inputValue, setInputValue] = useState('')

  const questionCount = messages.filter((m) => m.role === 'user').length

  function handleSend(text: string) {
    sendMessage(text)
    setInputValue('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* Header */}
      <div
        style={{
          flexShrink: 0,
          padding: '16px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg)',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#101620', letterSpacing: '-0.01em' }}>
            Chat
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--faint)', marginTop: 1 }}>
            {questionCount > 0
              ? `${questionCount} question${questionCount > 1 ? 's' : ''} this session`
              : 'New conversation'}
          </div>
        </div>

        {/* New conversation */}
        <button
          onClick={newConversation}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '8px 12px',
            borderRadius: 'calc(var(--radius) * 0.7)',
            border: '1px solid transparent',
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--accent)',
            cursor: 'pointer',
            background: 'transparent',
            fontFamily: 'inherit',
          }}
        >
          <PlusIcon size={14} color="var(--accent)" sw={2} />
          New
        </button>
      </div>

      {/* Messages */}
      <MessageList
        messages={messages}
        isLoading={isLoading}
        sources={sources}
        onSelectPrompt={(prompt) => setInputValue(prompt)}
      />

      {/* Error */}
      {error && (
        <div
          style={{
            margin: '0 28px 8px',
            maxWidth: 740,
            alignSelf: 'center',
            width: 'calc(100% - 56px)',
            padding: '10px 14px',
            background: '#FBEAEA',
            border: '1px solid #F0CECE',
            borderRadius: 'calc(var(--radius) * 0.7)',
            fontSize: 13,
            color: '#A23E3E',
          }}
        >
          {error}
        </div>
      )}

      {/* Composer */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        disabled={isLoading}
      />
    </div>
  )
}
