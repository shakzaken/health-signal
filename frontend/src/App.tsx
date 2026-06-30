import { useState } from 'react'
import Layout from './components/Layout'
import { type Tab } from './components/TabNav'
import UploadPage from './pages/UploadPage'
import ChatPage from './pages/ChatPage'
import ReportPage from './pages/ReportPage'
import LoginPage from './pages/LoginPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import AdminPage from './pages/AdminPage'
import { useChat } from './hooks/useChat'
import { useAuth } from './context/AuthContext'

function AppShell() {
  const { isAuthenticated, email } = useAuth()
  const [tab, setTab] = useState<Tab>('chat')
  const chatState = useChat(email ?? '')

  // Handle /verify-email?token=... route
  const params = new URLSearchParams(window.location.search)
  if (window.location.pathname === '/verify-email' && params.get('token')) {
    return <VerifyEmailPage token={params.get('token')!} />
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  if (window.location.pathname === '/admin') {
    return <AdminPage />
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
