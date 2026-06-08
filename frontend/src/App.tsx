import { useState } from 'react'
import Layout from './components/Layout'
import { type Tab } from './components/TabNav'
import UploadPage from './pages/UploadPage'
import ChatPage from './pages/ChatPage'
import ReportPage from './pages/ReportPage'
import LoginPage from './pages/LoginPage'
import { useChat } from './hooks/useChat'
import { useAuth } from './context/AuthContext'

function AppShell() {
  const { isAuthenticated } = useAuth()
  const [tab, setTab] = useState<Tab>('chat')
  const chatState = useChat()

  if (!isAuthenticated) {
    return <LoginPage />
  }

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

export default function App() {
  return <AppShell />
}
