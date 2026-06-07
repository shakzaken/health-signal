import { type ReactNode } from 'react'
import TabNav, { type Tab } from './TabNav'

interface LayoutProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  children: ReactNode
}

export default function Layout({ activeTab, onTabChange, children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">HealthSignal</h1>
      </header>
      <TabNav activeTab={activeTab} onTabChange={onTabChange} />
      <main className="flex-1 flex flex-col">{children}</main>
    </div>
  )
}
