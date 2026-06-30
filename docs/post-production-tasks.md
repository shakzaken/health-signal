# Post-Production Tasks — Health Signal

## Status: Planning

---

## Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Backups | ✅ Done |
| 2 | Monitoring | ✅ Done |
| 3 | Auth improvements | ✅ Done |
| 4 | Admin panel | 🔲 Not started |
| 5 | Answer quality (eval fixes) | 🔲 Not started |
| 6 | Auth & Google OAuth testing (production) | 🔲 Not started |
| 7 | PostgreSQL and Qdrant auth | 🔲 Not started |

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

### Task 4.3 — Google OAuth ✅

**Google Cloud Console**
- [x] Create a project in Google Cloud Console
- [x] Create OAuth 2.0 credentials (Web application, popup flow — no redirect URI needed)
- [x] Add authorized JavaScript origins: `https://healthsignal.yakirzaken.com` and `http://localhost:5173`
- [x] Note `GOOGLE_CLIENT_ID`

**Database**
- [x] Add columns to `users` table: `provider` (str, nullable), `provider_user_id` (str, nullable)
- [x] Write Alembic migration (`d5e6f7a8b9c0`)
- [x] `hashed_password` made nullable (Google users have no password)

**Backend**
- [x] Add `google-auth` to `backend/pyproject.toml`
- [x] Add `POST /auth/google/verify` — verifies Google ID token, finds or creates user, returns JWT
- [x] Existing email accounts are linked to Google on first Google login
- [x] Login endpoint guards against Google-only users trying to sign in with password
- [x] Add `GOOGLE_CLIENT_ID` to `backend/core/config.py` and `backend/.env` on server

**Frontend**
- [x] Add `@react-oauth/google` to `frontend/package.json`
- [x] Wrap app with `GoogleOAuthProvider` in `main.tsx`
- [x] Add `googleLogin()` to `AuthContext`
- [x] Add "Continue with Google" button with divider to login page
- [x] Add `VITE_GOOGLE_CLIENT_ID` to `frontend/Dockerfile` and `docker-compose.yml`
- [x] CI sources `frontend/.env` before build so `VITE_GOOGLE_CLIENT_ID` is baked into the bundle
- [x] Add `VITE_GOOGLE_CLIENT_ID` to `frontend/.env` on server

**Deploy**
- [ ] Copy updated `backend/.env` and `frontend/.env` to server
- [ ] Push to `main` — CI/CD deploys and tests Google login on production

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

## Phase 6 — Auth & Google OAuth testing (production)

### Task 6.1 — Password rules
- [ ] Register with password shorter than 8 chars → error: "Password must be at least 8 characters"
- [ ] Register with no uppercase → error: "Password must contain at least one uppercase letter"
- [ ] Register with no number → error: "Password must contain at least one number"
- [ ] Register with valid password (e.g. `Test1234`) → succeeds

### Task 6.2 — Email verification
- [ ] Register new user → "Check your email" screen appears
- [ ] Check spam folder note is visible
- [ ] Click verification link from email → redirected to app and logged in
- [ ] Try to login before verifying → 403 with clear message
- [ ] "Resend verification email" link works

### Task 6.3 — Google OAuth
- [ ] Click "Continue with Google" → Google account picker appears
- [ ] Select account → logged into app with correct email shown
- [ ] Log out → log back in with Google → works without re-consent
- [ ] Register a new email/password account, then log in with Google using same email → accounts linked, same user

---

## Phase 7 — PostgreSQL and Qdrant auth

**Why:** Both databases currently run with no authentication. Postgres uses `trust` mode (ignores passwords) and Qdrant has no API key. This should be tightened before real users are onboarded.

**Safe to do now** — no real users yet, so we can wipe and recreate all volumes cleanly.

### Task 7.1 — PostgreSQL: update docker-compose.yml
- [ ] Add `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` to the postgres service environment
- [ ] Remove `POSTGRES_HOST_AUTH_METHOD: trust`

### Task 7.2 — PostgreSQL: update env files
- [ ] Add `POSTGRES_PASSWORD=<your-password>` to `backend/.env`
- [ ] Add `POSTGRES_PASSWORD=<your-password>` to `ai-agent/.env`
- [ ] Verify `DATABASE_URL` in both `.env` files already has the correct matching password

### Task 7.3 — Qdrant: update docker-compose.yml
- [ ] Add `QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}` to the qdrant service environment

### Task 7.4 — Qdrant: update ai-agent code
- [ ] Add `qdrant_api_key: str = ""` to `ai-agent/core/config.py`
- [ ] Pass `api_key=settings.qdrant_api_key` to `QdrantClient` in `ai-agent/rag/qdrant_client.py`
- [ ] Add `QDRANT_API_KEY=<your-key>` to `ai-agent/.env`

### Task 7.5 — Wipe and recreate on server
```bash
cd /opt/health-signal
docker compose down -v        # stops containers AND deletes all volumes (postgres + qdrant + uploads)
docker compose up -d          # recreates everything fresh with auth enabled
```

### Task 7.6 — Verify
- [ ] `docker compose logs migrate` — migrations ran successfully
- [ ] `docker compose logs backend` — no database connection errors
- [ ] `docker compose logs ai-agent` — no Qdrant connection errors
- [ ] Upload a document and run a query — end-to-end works

---

## Deferred / future

- Move uploaded files to Cloudflare R2 (decouples file storage from server disk)
- pg_dump cron job (if/when 1-day data loss becomes unacceptable with paying users)
- Apple Sign In
- Phase 9 — Uptime Robot (moved to Phase 2 above)
