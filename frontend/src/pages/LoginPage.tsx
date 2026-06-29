import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { PulseIcon } from '../components/Icons'

type Mode = 'login' | 'register'

export default function LoginPage() {
  const { login, register, resendVerification } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [registered, setRegistered] = useState(false)
  const [unverified, setUnverified] = useState(false)
  const [resendSent, setResendSent] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email || !password) return
    setError('')
    setUnverified(false)
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password)
        setRegistered(true)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      if (msg.includes('verify your email')) {
        setUnverified(true)
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    setResendSent(false)
    try {
      await resendVerification(email)
      setResendSent(true)
    } catch {
      // Silent — backend always returns 200 to avoid enumeration
      setResendSent(true)
    }
  }

  if (registered) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font)', padding: 24 }}>
        <div style={{ width: '100%', maxWidth: 400, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✉️</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)', margin: '0 0 8px' }}>Check your email</h2>
          <p style={{ fontSize: 14, color: 'var(--sub)', margin: '0 0 8px' }}>
            We sent a verification link to <strong>{email}</strong>.<br />
            Click the link to activate your account.
          </p>
          <p style={{ fontSize: 13, color: 'var(--faint)', margin: '0 0 24px' }}>
            Don't see it? Check your spam or junk folder.
          </p>
          <button
            onClick={() => { setRegistered(false); setMode('login') }}
            style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 600, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            Back to sign in
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font)',
        padding: 24,
      }}
    >
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 36, justifyContent: 'center' }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'calc(var(--radius) * 0.7)',
              background: 'var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 1px 3px rgba(20,40,80,.22)',
            }}
          >
            <PulseIcon size={20} color="#fff" sw={2.1} />
          </div>
          <span style={{ fontWeight: 700, fontSize: 20, letterSpacing: '-0.01em', color: 'var(--ink)' }}>
            HealthSignal
          </span>
        </div>

        {/* Card */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '32px 28px',
            boxShadow: '0 2px 16px rgba(20,30,50,.07)',
          }}
        >
          <h1 style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink)', margin: '0 0 4px' }}>
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--sub)', margin: '0 0 24px' }}>
            {mode === 'login'
              ? 'Sign in to your health dashboard'
              : 'Start tracking your health data'}
          </p>

          <form onSubmit={handleSubmit}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Email */}
              <div>
                <label
                  style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--sub)', marginBottom: 6 }}
                >
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid var(--border-strong)',
                    borderRadius: 'calc(var(--radius) * 0.6)',
                    fontSize: 14,
                    color: 'var(--ink)',
                    background: 'var(--surface)',
                    fontFamily: 'inherit',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                  onFocus={(e) => { e.target.style.borderColor = 'var(--accent)'; e.target.style.boxShadow = '0 0 0 3px var(--accent-soft)' }}
                  onBlur={(e) => { e.target.style.borderColor = 'var(--border-strong)'; e.target.style.boxShadow = 'none' }}
                />
              </div>

              {/* Password */}
              <div>
                <label
                  style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--sub)', marginBottom: 6 }}
                >
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid var(--border-strong)',
                    borderRadius: 'calc(var(--radius) * 0.6)',
                    fontSize: 14,
                    color: 'var(--ink)',
                    background: 'var(--surface)',
                    fontFamily: 'inherit',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                  onFocus={(e) => { e.target.style.borderColor = 'var(--accent)'; e.target.style.boxShadow = '0 0 0 3px var(--accent-soft)' }}
                  onBlur={(e) => { e.target.style.borderColor = 'var(--border-strong)'; e.target.style.boxShadow = 'none' }}
                />
              </div>

              {/* Error */}
              {error && (
                <div style={{ padding: '9px 12px', background: '#FBEAEA', border: '1px solid #F0CECE', borderRadius: 'calc(var(--radius) * 0.5)', fontSize: 13, color: '#A23E3E' }}>
                  {error}
                </div>
              )}

              {/* Unverified account */}
              {unverified && (
                <div style={{ padding: '9px 12px', background: '#FFF8E1', border: '1px solid #FFE082', borderRadius: 'calc(var(--radius) * 0.5)', fontSize: 13, color: '#7A5A00' }}>
                  Please verify your email before signing in.{' '}
                  {resendSent ? (
                    <span style={{ color: '#2E7D32', fontWeight: 600 }}>Email sent!</span>
                  ) : (
                    <button onClick={handleResend} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 600, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', padding: 0 }}>
                      Resend verification email
                    </button>
                  )}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '11px',
                  background: loading ? 'var(--border-strong)' : 'var(--accent)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'calc(var(--radius) * 0.6)',
                  fontSize: 14,
                  fontWeight: 600,
                  fontFamily: 'inherit',
                  cursor: loading ? 'default' : 'pointer',
                  transition: 'background .15s',
                  marginTop: 4,
                }}
              >
                {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              </button>
            </div>
          </form>

          {/* Toggle mode */}
          <div style={{ marginTop: 20, textAlign: 'center', fontSize: 13, color: 'var(--sub)' }}>
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent)',
                fontWeight: 600,
                fontSize: 13,
                cursor: 'pointer',
                fontFamily: 'inherit',
                padding: 0,
              }}
            >
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </div>
        </div>

        <div style={{ marginTop: 16, textAlign: 'center', fontSize: 11.5, color: 'var(--faint)' }}>
          AI · not medical advice
        </div>
      </div>
    </div>
  )
}
