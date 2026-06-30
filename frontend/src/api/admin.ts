import { triggerSessionExpired } from './sessionEvents'

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'hs_token'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY)
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  })
  if (res.status === 401) {
    triggerSessionExpired()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export interface AdminStats {
  total_users: number
  total_queries: number
  total_ingestions: number
  active_users_7d: number
  active_users_30d: number
}

export interface AdminUser {
  id: string
  email: string
  created_at: string
  last_login_at: string | null
  documents_ingested: number
  queries_sent: number
  is_verified: boolean
  is_test_user: boolean
}

export async function fetchAdminStats(): Promise<AdminStats> {
  return adminRequest<AdminStats>('/api/admin/stats')
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  return adminRequest<AdminUser[]>('/api/admin/users')
}

export async function createAdminUser(email: string, password: string, isTestUser: boolean): Promise<AdminUser> {
  return adminRequest<AdminUser>('/api/admin/users', {
    method: 'POST',
    body: JSON.stringify({ email, password, is_test_user: isTestUser }),
  })
}

export async function verifyAdminUser(userId: string): Promise<void> {
  await adminRequest(`/api/admin/users/${userId}/verify`, { method: 'POST' })
}

export async function deleteAdminUser(userId: string, confirmEmail: string): Promise<void> {
  await adminRequest(`/api/admin/users/${userId}`, {
    method: 'DELETE',
    body: JSON.stringify({ confirm_email: confirmEmail }),
  })
}
