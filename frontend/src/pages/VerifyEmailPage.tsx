import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { PulseIcon } from '../components/Icons'

export default function VerifyEmailPage({ token }: { token: string }) {
  const { verifyEmail } = useAuth()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Verification failed')
        setStatus('error')
      })
  }, [token, verifyEmail])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font)', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 400, textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 36, justifyContent: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 'calc(var(--radius) * 0.7)', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <PulseIcon size={20} color="#fff" sw={2.1} />
          </div>
          <span style={{ fontWeight: 700, fontSize: 20, letterSpacing: '-0.01em', color: 'var(--ink)' }}>HealthSignal</span>
        </div>

        {status === 'loading' && (
          <>
            <p style={{ fontSize: 16, color: 'var(--sub)' }}>Verifying your email…</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)', margin: '0 0 8px' }}>Email verified!</h2>
            <p style={{ fontSize: 14, color: 'var(--sub)', margin: '0 0 24px' }}>Your account is now active. You're being signed in…</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✗</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)', margin: '0 0 8px' }}>Verification failed</h2>
            <p style={{ fontSize: 14, color: '#A23E3E', margin: '0 0 24px' }}>{error}</p>
            <a href="/" style={{ color: 'var(--accent)', fontWeight: 600, fontSize: 14 }}>Back to sign in</a>
          </>
        )}
      </div>
    </div>
  )
}
