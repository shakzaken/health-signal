import { useState } from 'react'
import type { useChat } from '../hooks/useChat'
import MessageList from '../components/MessageList'
import ChatInput from '../components/ChatInput'
import { FilterIcon, ChevronIcon, PlusIcon } from '../components/Icons'

type ChatState = ReturnType<typeof useChat>

interface ChatPageProps {
  chatState: ChatState
}

const DOCUMENT_TYPES = [
  { value: '', label: 'All documents' },
  { value: 'lab_result', label: 'Blood tests' },
  { value: 'symptom_log', label: 'Symptom logs' },
  { value: 'supplement_log', label: 'Supplement records' },
  { value: 'doctor_note', label: 'Doctor notes' },
]

export default function ChatPage({ chatState }: ChatPageProps) {
  const { messages, isLoading, sources, error, sendMessage, newConversation } = chatState
  const [documentType, setDocumentType] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [inputValue, setInputValue] = useState('')

  const currentFilterLabel = DOCUMENT_TYPES.find((t) => t.value === documentType)?.label ?? 'All documents'
  const questionCount = messages.filter((m) => m.role === 'user').length

  function handleSend(text: string) {
    sendMessage(text, documentType || undefined)
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

        {/* Right side: filter + new */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        {/* Filter dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setFilterOpen((o) => !o)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 12px',
              border: '1px solid var(--border-strong)',
              borderRadius: 'calc(var(--radius) * 0.7)',
              fontSize: 13,
              color: 'var(--sub)',
              background: 'var(--surface)',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            <FilterIcon size={14} color="var(--accent)" />
            {currentFilterLabel}
            <span
              style={{
                display: 'flex',
                transition: 'transform .2s',
                transform: filterOpen ? 'rotate(180deg)' : 'none',
              }}
            >
              <ChevronIcon size={12} color="var(--faint)" />
            </span>
          </button>

          {filterOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                zIndex: 20,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'calc(var(--radius) * 0.7)',
                boxShadow: '0 8px 28px rgba(20,30,50,.14)',
                padding: 5,
                width: 210,
              }}
            >
              {DOCUMENT_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => {
                    setDocumentType(t.value)
                    setFilterOpen(false)
                  }}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 9,
                    padding: '9px 10px',
                    border: 'none',
                    background: t.value === documentType ? 'var(--accent-soft)' : 'transparent',
                    borderRadius: 7,
                    fontSize: 13,
                    color: t.value === documentType ? 'var(--accent-ink)' : 'var(--sub)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontWeight: t.value === documentType ? 600 : 400,
                  }}
                >
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      flexShrink: 0,
                      background: t.value === documentType ? 'var(--accent)' : 'var(--border-strong)',
                    }}
                  />
                  {t.label}
                </button>
              ))}
            </div>
          )}
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
        </div> {/* end right-side group */}
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
