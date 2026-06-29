# Post-Production Tasks — Health Signal

## Status: Planning

---

## Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Backups | 🔲 Not started |
| 2 | Monitoring | ✅ Done |
| 3 | Auth improvements | 🔄 In progress |
| 4 | Admin panel | 🔲 Not started |
| 5 | Answer quality (eval fixes) | 🔲 Not started |

---

## Phase 1 — Backups ✅

### Task 1.1 — Enable Hetzner server backups ✅

- [x] Go to Hetzner dashboard → server → Backups tab
- [x] Enable backups (one checkbox, ~€2.00/month — 20% of CX33 cost)
- [ ] Verify first snapshot appears within 24 hours

---

## Phase 2 — Monitoring

### Task 2.1 — Uptime Robot ✅

- [x] Create account at uptimerobot.com (free tier, forever free)
- [x] Add monitor for `https://healthsignal.yakirzaken.com` (HTTPS, every 5 minutes)
- [x] Configure email alert for downtime

### Task 2.2 — Sentry (error tracking) ✅

**Backend**
- [x] Create Sentry account and project (Python/FastAPI)
- [x] Add `sentry-sdk[fastapi]` to `backend/pyproject.toml`
- [x] Initialize Sentry in `backend/main.py` with `SENTRY_DSN` env var
- [x] Add `SENTRY_DSN` to `backend/.env` locally — tested, events confirmed in Sentry dashboard
- [x] Add `SENTRY_DSN` to `backend/.env` on server

**AI-Agent**
- [x] Create Sentry project (Python/FastAPI)
- [x] Add `sentry-sdk[fastapi]` to `ai-agent/pyproject.toml`
- [x] Initialize Sentry in `ai-agent/main.py` with `SENTRY_DSN` env var
- [x] Add `SENTRY_DSN` to `ai-agent/.env` locally — tested, events confirmed in Sentry dashboard
- [x] Add `SENTRY_DSN` to `ai-agent/.env` on server

**Frontend**
- [x] Create Sentry project (React)
- [x] Add `@sentry/react` to `frontend/package.json`
- [x] Initialize Sentry in `frontend/src/main.tsx` with `VITE_SENTRY_DSN`
- [x] Add `VITE_SENTRY_DSN` build arg to `frontend/Dockerfile` and `docker-compose.yml`
- [x] Add `VITE_SENTRY_DSN` to `frontend/.env.local` locally
- [x] Add `VITE_SENTRY_DSN` to root `.env` on server
- [x] Test frontend Sentry in production after deploy — errors confirmed in Sentry dashboard
- [x] Added `Sentry.ErrorBoundary` wrapper in `main.tsx` to capture React render errors

**Deploy**
- [x] Pushed to `main` — all services rebuilt with Sentry enabled

---

## Phase 3 — Auth improvements

### Task 4.1 — Password rules ✅

- [x] Add Pydantic validator on the register endpoint (`backend/schemas/auth.py`)
- [x] Rules: min 8 characters + at least 1 uppercase + at least 1 number
- [x] Return clear error message if validation fails
- [x] QA tested — 15/15 cases passing

### Task 4.2 — Email confirmation 🔄 In progress

**Database**
- [x] Add columns to `users` table: `is_verified` (bool, default false), `verification_token` (str, nullable), `verification_token_expires_at` (datetime, nullable)
- [x] Write Alembic migration (`c4d5e6f7a8b9_add_email_verification_to_users.py`)

**Backend**
- [x] On register (production): generate secure token, save to DB with 24h expiry, send verification email
- [x] On register (dev): auto-verify, return token immediately — no email sent
- [x] Add `POST /auth/verify-email?token=...` endpoint — validates token, marks user as verified, returns JWT
- [x] Block login for unverified users in production (403 with clear message)
- [x] Add `POST /auth/resend-verification` endpoint
- [x] Add `resend` to `backend/pyproject.toml`
- [x] Write email template in `backend/services/email_service.py`
- [x] Add `RESEND_API_KEY` and `FRONTEND_URL` to `backend/core/config.py`

**Email (Resend) — pending setup**
- [ ] Create Resend account at resend.com
- [ ] Add DNS records to Cloudflare (SPF, DKIM) for `yakirzaken.com`
- [ ] Verify domain in Resend dashboard
- [ ] Get API key and add `RESEND_API_KEY` to `backend/.env` on server

**Frontend**
- [x] Show "Check your email" screen after registration (production only)
- [x] Handle `/verify-email?token=...` route — `VerifyEmailPage.tsx`
- [x] Show "Resend verification email" link on login if account is unverified

### Task 4.3 — Google OAuth

**Google Cloud Console**
- [ ] Create a project in Google Cloud Console
- [ ] Enable Google Identity API
- [ ] Create OAuth 2.0 credentials — set authorized redirect URI to `https://healthsignal.yakirzaken.com/auth/google/callback`
- [ ] Note `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

**Database**
- [ ] Add columns to `users` table: `provider` (str, nullable), `provider_user_id` (str, nullable)
- [ ] Write Alembic migration
- [ ] `password_hash` becomes nullable (Google users have no password)

**Backend**
- [ ] Add `GET /auth/google` — redirects user to Google OAuth consent screen
- [ ] Add `GET /auth/google/callback` — exchanges code for user info, finds or creates user, returns JWT
- [ ] Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `backend/.env` on server
- [ ] Google users are created as already verified (no email confirmation needed)

**Frontend**
- [ ] Add "Continue with Google" button to login and register pages
- [ ] Handle redirect flow (navigate to `/auth/google`, handle return with token)

---

## Phase 4 — Admin panel

### Task 5.1 — Usage tracking (backend)

**Database**
- [ ] Add `is_test_user` boolean column to `users` table (default false)
- [ ] Add `usage_events` table: `id`, `user_id`, `event_type` (query / ingestion), `created_at`
- [ ] Write Alembic migration

**Backend — event recording**
- [ ] Record `ingestion` event when a document is successfully ingested
- [ ] Record `query` event when a chat message is sent

**Backend — admin API endpoints** (all require `current_user.email == ADMIN_EMAIL`)
- [ ] `GET /admin/stats` — summary cards: total users, total queries, total ingestions, active users (7d, 30d)
- [ ] `GET /admin/users` — list of all real users (exclude `is_test_user=true`) with per-user stats
- [ ] `POST /admin/users` — create user (email, password, `is_test_user` flag) — created as verified
- [ ] `POST /admin/users/{id}/verify` — manually verify an unverified user
- [ ] Add `ADMIN_EMAIL` to `backend/.env` on server

### Task 5.2 — Admin frontend

- [ ] Add protected `/admin` route — redirects to login if not authenticated as admin
- [ ] Summary cards: total users, total queries, total ingestions, active users (7d / 30d)
- [ ] Users table: email, registration date, last login, documents ingested, queries sent, verified status
- [ ] Create user form: email + password + "Test / automation user" checkbox
- [ ] Verify user button next to unverified users in the table

### Task 5.3 — Cloudflare Access (Zero Trust)

- [ ] Go to Cloudflare dashboard → Zero Trust → Access → Applications
- [ ] Create application: protect `healthsignal.yakirzaken.com/admin*`
- [ ] Set policy: allow only `shakzaken@gmail.com` via Google login
- [ ] Verify `/admin` is blocked for all other users

---

## Phase 5 — Answer quality (eval fixes)

### Task 5.1 — Fix supervisor routing

5 cases in test 002 incorrectly route to `lab_analysis` instead of the correct agent. All require fixes to `CLASSIFY_PROMPT` in `ai-agent/agents/supervisor.py`.

| Case | Question | Actual route | Expected route |
|------|----------|-------------|----------------|
| pattern_03 | "What happened during intense work in October?" | lab_analysis | pattern_detection |
| pattern_04 | "What health changes around the lifestyle changes?" | lab_analysis | pattern_detection |
| timeline_01 | "Give me a chronological summary of my health in 2024" | lab_analysis | timeline |
| timeline_04 | "When did Daniel's energy levels start improving?" | lab_analysis | timeline |
| rag_01 | "Why did Daniel start taking selenium?" | lab_analysis | rag |

- [ ] Fix `CLASSIFY_PROMPT` in `ai-agent/agents/supervisor.py`
- [ ] Re-run test 002 — target 21/21
- [ ] Re-run test 001 — confirm no regressions (target 20/20)

---

## Deferred / future

- Move uploaded files to Cloudflare R2 (decouples file storage from server disk)
- pg_dump cron job (if/when 1-day data loss becomes unacceptable with paying users)
- Apple Sign In
- Phase 9 — Uptime Robot (moved to Phase 2 above)
