import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './context/AuthContext.tsx'

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({ dsn: import.meta.env.VITE_SENTRY_DSN })
}


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
