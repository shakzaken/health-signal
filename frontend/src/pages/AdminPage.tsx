import { useEffect, useState, useCallback } from 'react'
import { fetchAdminStats, fetchAdminUsers, createAdminUser, verifyAdminUser, type AdminStats, type AdminUser } from '../api/admin'

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString()
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '18px 20px',
        flex: 1,
        minWidth: 140,
      }}
    >
      <div style={{ fontSize: 12.5, color: 'var(--sub)', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink)' }}>{value}</div>
    </div>
  )
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [accessDenied, setAccessDenied] = useState(false)

  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newIsTestUser, setNewIsTestUser] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [statsData, usersData] = await Promise.all([fetchAdminStats(), fetchAdminUsers()])
      setStats(statsData)
      setUsers(usersData)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load admin data'
      if (message.startsWith('403')) {
        setAccessDenied(true)
      } else {
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault()
    setCreateError('')
    setCreating(true)
    try {
      await createAdminUser(newEmail, newPassword, newIsTestUser)
      setNewEmail('')
      setNewPassword('')
      setNewIsTestUser(false)
      await load()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create user')
    } finally {
      setCreating(false)
    }
  }

  async function handleVerify(userId: string) {
    try {
      await verifyAdminUser(userId)
      await load()
    } catch {
      // surfaced via reload failing silently — acceptable for an admin-only tool
    }
  }

  if (accessDenied) {
    return (
      <div style={{ padding: 40, fontFamily: 'var(--font)', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--ink)' }}>Access denied</h2>
        <p style={{ color: 'var(--sub)' }}>You don't have permission to view this page.</p>
      </div>
    )
  }

  return (
    <div style={{ padding: 24, fontFamily: 'var(--font)', maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)', marginBottom: 20 }}>Admin Dashboard</h1>

      {error && (
        <div style={{ padding: '9px 12px', background: '#FBEAEA', border: '1px solid #F0CECE', borderRadius: 'calc(var(--radius) * 0.5)', fontSize: 13, color: '#A23E3E', marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--sub)' }}>Loading…</p>
      ) : (
        <>
          {stats && (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 28 }}>
              <StatCard label="Total users" value={stats.total_users} />
              <StatCard label="Total queries" value={stats.total_queries} />
              <StatCard label="Total ingestions" value={stats.total_ingestions} />
              <StatCard label="Active (7d)" value={stats.active_users_7d} />
              <StatCard label="Active (30d)" value={stats.active_users_30d} />
            </div>
          )}

          {/* Create user form */}
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: 20,
              marginBottom: 28,
            }}
          >
            <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)', margin: '0 0 14px' }}>Create user</h2>
            <form onSubmit={handleCreateUser} style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              <input
                type="email"
                placeholder="email@example.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
                style={{ flex: '1 1 200px', padding: '8px 10px', border: '1px solid var(--border-strong)', borderRadius: 'calc(var(--radius) * 0.5)', fontSize: 13, fontFamily: 'inherit' }}
              />
              <input
                type="password"
                placeholder="Password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                style={{ flex: '1 1 160px', padding: '8px 10px', border: '1px solid var(--border-strong)', borderRadius: 'calc(var(--radius) * 0.5)', fontSize: 13, fontFamily: 'inherit' }}
              />
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--sub)' }}>
                <input type="checkbox" checked={newIsTestUser} onChange={(e) => setNewIsTestUser(e.target.checked)} />
                Test / automation user
              </label>
              <button
                type="submit"
                disabled={creating}
                style={{ padding: '8px 16px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 'calc(var(--radius) * 0.5)', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
              >
                {creating ? 'Creating…' : 'Create'}
              </button>
            </form>
            {createError && <div style={{ marginTop: 10, fontSize: 13, color: '#A23E3E' }}>{createError}</div>}
          </div>

          {/* Users table */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--bg)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}>Email</th>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}>Registered</th>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}>Last login</th>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}>Documents</th>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}>Queries</th>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}>Verified</th>
                  <th style={{ padding: '10px 14px', color: 'var(--sub)', fontWeight: 600 }}></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 14px', color: 'var(--ink)' }}>{u.email}</td>
                    <td style={{ padding: '10px 14px', color: 'var(--sub)' }}>{formatDate(u.created_at)}</td>
                    <td style={{ padding: '10px 14px', color: 'var(--sub)' }}>{formatDate(u.last_login_at)}</td>
                    <td style={{ padding: '10px 14px', color: 'var(--sub)' }}>{u.documents_ingested}</td>
                    <td style={{ padding: '10px 14px', color: 'var(--sub)' }}>{u.queries_sent}</td>
                    <td style={{ padding: '10px 14px' }}>
                      {u.is_verified ? (
                        <span style={{ color: '#2E7D32', fontWeight: 600 }}>Yes</span>
                      ) : (
                        <span style={{ color: '#A23E3E', fontWeight: 600 }}>No</span>
                      )}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      {!u.is_verified && (
                        <button
                          onClick={() => handleVerify(u.id)}
                          style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 600, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit', padding: 0 }}
                        >
                          Verify
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
