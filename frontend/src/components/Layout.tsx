import { type ReactNode } from 'react'
import { type Tab } from './TabNav'
import { type Session } from '../types'
import { PulseIcon, ChatIcon, UploadIcon, ReportIcon } from './Icons'

interface LayoutProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  children: ReactNode
  sessions: Session[]
  onRestoreSession: (session: Session) => void
}

const NAV_ITEMS: { id: Tab; label: string; Icon: React.FC<{ size?: number; color?: string; sw?: number }> }[] = [
  { id: 'chat', label: 'Chat', Icon: ChatIcon },
  { id: 'upload', label: 'Upload', Icon: UploadIcon },
  { id: 'report', label: 'Doctor Report', Icon: ReportIcon },
]

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: ReactNode
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: 11,
        padding: '10px 12px',
        borderRadius: 'calc(var(--radius) * 0.7)',
        background: active ? 'var(--surface)' : 'transparent',
        color: active ? 'var(--ink)' : 'var(--sub)',
        fontWeight: active ? 600 : 500,
        fontSize: 14,
        cursor: 'pointer',
        border: active ? '1px solid var(--border)' : '1px solid transparent',
        boxShadow: active ? '0 1px 2px rgba(20,30,50,.05)' : 'none',
        fontFamily: 'inherit',
        textAlign: 'left',
        transition: 'background .12s, color .12s',
      }}
    >
      <span style={{ color: active ? 'var(--accent)' : 'var(--faint)', display: 'flex' }}>{icon}</span>
      {label}
    </button>
  )
}

export default function Layout({ activeTab, onTabChange, children, sessions, onRestoreSession }: LayoutProps) {
  return (
    <div
      style={{
        fontFamily: 'var(--font)',
        color: 'var(--ink)',
        height: '100vh',
        display: 'flex',
        background: 'var(--bg)',
        WebkitFontSmoothing: 'antialiased',
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          flex: '0 0 248px',
          background: 'var(--sidebar)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          padding: '18px 14px',
          overflow: 'hidden',
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '4px 8px 22px',
          }}
        >
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 'calc(var(--radius) * 0.7)',
              background: 'var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 1px 3px rgba(20,40,80,.22)',
              flexShrink: 0,
            }}
          >
            <PulseIcon size={17} color="#fff" sw={2.1} />
          </div>
          <span
            style={{
              fontWeight: 700,
              fontSize: 17,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
            }}
          >
            HealthSignal
          </span>
        </div>

        {/* Nav items */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NAV_ITEMS.map(({ id, label, Icon }) => (
            <NavItem
              key={id}
              icon={<Icon size={18} />}
              label={label}
              active={activeTab === id}
              onClick={() => onTabChange(id)}
            />
          ))}
        </div>

        {/* Recent chats */}
        {sessions.length > 0 && (
          <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div
              style={{
                padding: '0 8px 9px',
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: '.06em',
                textTransform: 'uppercase',
                color: 'var(--faint)',
              }}
            >
              Recent chats
            </div>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                overflowY: 'auto',
                flex: 1,
              }}
            >
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => onRestoreSession(session)}
                  style={{
                    textAlign: 'left',
                    padding: '9px 12px',
                    borderRadius: 'calc(var(--radius) * 0.6)',
                    fontSize: 13,
                    color: 'var(--sub)',
                    fontWeight: 400,
                    background: 'transparent',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    border: 'none',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    transition: 'background .1s, color .1s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--surface-2)'
                    e.currentTarget.style.color = 'var(--ink)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent'
                    e.currentTarget.style.color = 'var(--sub)'
                  }}
                >
                  <span
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: '50%',
                      flexShrink: 0,
                      background: 'var(--border-strong)',
                    }}
                  />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {session.title}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            marginTop: 'auto',
            padding: '12px 8px 4px',
            borderTop: '1px solid var(--border)',
          }}
        >
          <div style={{ fontSize: 12, color: 'var(--faint)', lineHeight: 1.5 }}>
            Personal health assistant
          </div>
          <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 2 }}>
            AI · not medical advice
          </div>
        </div>
      </div>

      {/* Main content */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg)',
          overflow: 'hidden',
        }}
      >
        {children}
      </div>
    </div>
  )
}
