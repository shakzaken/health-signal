import { useState } from 'react'
import { useChat } from '../hooks/useChat'
import MessageList from '../components/MessageList'
import ChatInput from '../components/ChatInput'
import SourcePanel from '../components/SourcePanel'

const DOCUMENT_TYPES = [
  { value: '', label: 'All documents' },
  { value: 'lab_result', label: 'Lab results' },
  { value: 'symptom_log', label: 'Symptom logs' },
  { value: 'supplement_log', label: 'Supplement logs' },
  { value: 'doctor_note', label: 'Doctor notes' },
]

export default function ChatPage() {
  const { messages, isLoading, sources, error, sendMessage, newConversation } = useChat()
  const [documentType, setDocumentType] = useState('')

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full">

      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white">
        <select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-700"
        >
          {DOCUMENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        <button
          onClick={newConversation}
          className="text-sm text-gray-500 hover:text-gray-800 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        >
          New conversation
        </button>
      </div>

      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} />

      {/* Error */}
      {error && (
        <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Sources */}
      <SourcePanel sources={sources} />

      {/* Input */}
      <ChatInput
        onSend={(text) => sendMessage(text, documentType || undefined)}
        disabled={isLoading}
      />
    </div>
  )
}
