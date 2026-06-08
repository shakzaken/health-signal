import { useState } from 'react'
import Layout from './components/Layout'
import { type Tab } from './components/TabNav'
import UploadPage from './pages/UploadPage'
import ChatPage from './pages/ChatPage'
import ReportPage from './pages/ReportPage'
import { useChat } from './hooks/useChat'

export default function App() {
  const [tab, setTab] = useState<Tab>('chat')
  const chatState = useChat()

  return (
    <Layout
      activeTab={tab}
      onTabChange={setTab}
      sessions={chatState.sessions}
      onRestoreSession={(session) => {
        chatState.restoreSession(session)
        setTab('chat')
      }}
    >
      {tab === 'upload' && <UploadPage />}
      {tab === 'chat' && <ChatPage chatState={chatState} />}
      {tab === 'report' && <ReportPage />}
    </Layout>
  )
}
