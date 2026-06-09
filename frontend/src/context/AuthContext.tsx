import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

const TOKEN_KEY = 'hs_token'
const EMAIL_KEY = 'hs_email'
const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

interface AuthContextValue {
  token: string | null
  email: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
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
      throw new Error(data.detail ?? 'Login failed')
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
      throw new Error(data.detail ?? 'Registration failed')
    }
    const data = await res.json()
    saveSession(data.access_token, email)
  }, [saveSession])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
    setToken(null)
    setEmail(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, email, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
