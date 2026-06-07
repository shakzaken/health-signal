import { useState } from 'react'
import Layout from './components/Layout'
import { type Tab } from './components/TabNav'
import UploadPage from './pages/UploadPage'
import ChatPage from './pages/ChatPage'
import ReportPage from './pages/ReportPage'

export default function App() {
  const [tab, setTab] = useState<Tab>('chat')

  return (
    <Layout activeTab={tab} onTabChange={setTab}>
      {tab === 'upload' && <UploadPage />}
      {tab === 'chat' && <ChatPage />}
      {tab === 'report' && <ReportPage />}
    </Layout>
  )
}
