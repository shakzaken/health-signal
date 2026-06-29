import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

function extractDetail(data: Record<string, unknown>, fallback: string): string {
  const detail = data.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const msg = typeof e === 'object' && e !== null && 'msg' in e ? String(e.msg) : String(e)
        return msg.replace(/^Value error,\s*/i, '')
      })
      .join(', ')
  }
  return fallback
}

const TOKEN_KEY = 'hs_token'
const EMAIL_KEY = 'hs_email'
const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

interface AuthContextValue {
  token: string | null
  email: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  googleLogin: (credential: string) => Promise<void>
  verifyEmail: (token: string) => Promise<void>
  resendVerification: (email: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem(EMAIL_KEY))

  const saveSession = useCallback((t: string, e: string) => {
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(EMAIL_KEY, e)
    setToken(t)
    setEmail(e)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(extractDetail(data, 'Login failed'))
    }
    const data = await res.json()
    saveSession(data.access_token, email)
  }, [saveSession])

  const register = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(extractDetail(data, 'Registration failed'))
    }
    const data = await res.json()
    // In dev, backend returns a token directly (no email verification)
    if (data.access_token) {
      saveSession(data.access_token, email)
    }
    // In production, no token returned — user must verify email first
  }, [saveSession])

  const googleLogin = useCallback(async (credential: string) => {
    // Extract email from the Google ID token before sending to backend
    let userEmail = ''
    try {
      const googlePayload = JSON.parse(atob(credential.split('.')[1]))
      userEmail = googlePayload.email ?? ''
    } catch { /* ignore — saveSession will use empty string */ }

    const res = await fetch(`${BASE_URL}/auth/google/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(extractDetail(data, 'Google login failed'))
    }
    const data = await res.json()
    saveSession(data.access_token, userEmail)
  }, [saveSession])

  const verifyEmail = useCallback(async (token: string) => {
    const res = await fetch(`${BASE_URL}/auth/verify-email?token=${encodeURIComponent(token)}`, {
      method: 'POST',
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(extractDetail(data, 'Verification failed'))
    }
    const data = await res.json()
    // We don't have the email here — store token only, email will be missing
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setToken(data.access_token)
  }, [])

  const resendVerification = useCallback(async (email: string) => {
    const res = await fetch(`${BASE_URL}/auth/resend-verification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(extractDetail(data, 'Failed to resend verification email'))
    }
  }, [])

  const logout = useCallback(() => {
    // Clear active session for this user before removing email
    const currentEmail = localStorage.getItem(EMAIL_KEY)
    if (currentEmail) {
      localStorage.removeItem(`hs_active_session_${currentEmail}`)
    }
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
    setToken(null)
    setEmail(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, email, isAuthenticated: !!token, login, register, googleLogin, verifyEmail, resendVerification, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
