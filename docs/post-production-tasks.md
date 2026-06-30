# Post-Production Tasks — Health Signal

## Status: Planning

---

## Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Backups | ✅ Done |
| 2 | Monitoring | ✅ Done |
| 3 | Auth improvements | ✅ Done |
| 4 | Admin panel | ✅ Done |
| 5 | Answer quality (eval fixes) | 🔲 Not started |
| 6 | Auth & Google OAuth testing (production) | 🔄 Google OAuth done, password/email verification pending |
| 7 | PostgreSQL and Qdrant auth | ✅ Done |
| 8 | Session expiry reload-loop fix | ✅ Done |

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

## Phase 4 — Admin panel ✅

### Task 5.1 — Usage tracking (backend) ✅

**Database**
- [x] Add `is_test_user` boolean column to `users` table (default false)
- [x] Add `last_login_at` column to `users` table (nullable) — set on every successful login (password + Google)
- [x] Add `usage_events` table: `id`, `user_id`, `event_type` (query / ingestion), `created_at`
- [x] Write Alembic migration (`e6f7a8b9c0d1_add_usage_tracking.py`)

**Backend — event recording**
- [x] Record `ingestion` event when a document is successfully ingested (`DocumentService._trigger_ingestion`)
- [x] Record `query` event when a chat message is sent (both `/api/ai/query` and `/api/ai/query/stream`)

**Backend — admin API endpoints** (all require `current_user.email == ADMIN_EMAIL`)
- [x] `GET /api/admin/stats` — summary cards: total users, total queries, total ingestions, active users (7d, 30d)
- [x] `GET /api/admin/users` — list of all real users (exclude `is_test_user=true`) with per-user stats
- [x] `POST /api/admin/users` — create user (email, password, `is_test_user` flag) — created as verified
- [x] `POST /api/admin/users/{id}/verify` — manually verify an unverified user
- [x] Add `ADMIN_EMAIL` to `backend/.env` on server
- [x] Admin routes use `/api/admin` prefix (not bare `/admin`) to avoid colliding with the frontend's `/admin` page route — see API prefix migration note below

### Task 5.2 — Admin frontend ✅

- [x] Add protected `/admin` route — shows "Access denied" if not authenticated as admin (backend returns 403)
- [x] Summary cards: total users, total queries, total ingestions, active users (7d / 30d)
- [x] Users table: email, registration date, last login, documents ingested, queries sent, verified status
- [x] Create user form: email + password + "Test / automation user" checkbox
- [x] Verify user button next to unverified users in the table
- [x] QA tested locally end-to-end: ingestion + query events recorded correctly, verify button works, test users correctly excluded from view but created in DB

### Task 5.3 — Cloudflare Access (Zero Trust) ✅

- [x] Go to Cloudflare dashboard → Zero Trust → Access → Applications
- [x] Create application: protect `healthsignal.yakirzaken.com/admin*` AND `healthsignal.yakirzaken.com/api/admin*` (both needed — page and API are separate paths)
- [x] Set policy: allow only `shakzaken@gmail.com` via Google login
- [x] Free tier — well under the 50-user Zero Trust limit
- [x] Verified backend/ai-agent/qdrant are not directly reachable from the internet (only nginx publishes ports 80/443) — Cloudflare Access has no bypass route

### Task 5.4 — API route prefix migration ✅

**Why:** The admin frontend page (`/admin`) and the admin backend API (originally also `/admin/*`) collided — nginx routed `/admin/stats` to the SPA instead of the backend. Fixed by moving **all** backend API routes under `/api/*` for both `backend` and `ai-agent` services, and simplifying nginx to a single `location /api/`.

- [x] Backend: all 9 routers (`auth`, `ai`, `documents`, `conversations`, `lab-results`, `timeline`, `supplement-entries`, `symptom-entries`, `admin`, `health`) now under `/api/*`
- [x] ai-agent: all 4 routers (`query`, `ingest`, `report`, `health`) now under `/api/*`
- [x] nginx.conf simplified from an enumerated regex to `location /api/` — no more manual updates needed per new route
- [x] Frontend (`AuthContext.tsx`, `backend.ts`, `admin.ts`) updated to call `/api/*`
- [x] Backend → ai-agent internal calls updated (`ai_agent.py` proxy, `document_service.py`)
- [x] **Found and fixed a production-breaking bug**: ai-agent → backend internal calls (conversation memory, lab/timeline/symptom/supplement tools) still used old un-prefixed paths — caused silent 404s in production, no Sentry alert. Fixed all 12 call sites across 6 files.
- [x] Backend + ai-agent test suites confirmed zero regressions (same pre-existing failure counts before/after)

### Task 5.5 — Silent error handling audit ✅

**Why:** The bug above was invisible in Sentry because failures were caught and logged at `warning` level. Sentry's default logging integration only auto-captures `error`-level logs as events.

- [x] `ai-agent/tools/symptom_extractor.py`, `lab_extractor.py`, `supplement_extractor.py` — were silently swallowing extraction failures with zero logging; added `logger.error`
- [x] `ai-agent/agents/supervisor.py` — classification failures silently fell back to `rag` route with no log; added `logger.error`
- [x] `ai-agent/agents/conversation_memory.py` (3 sites), `doctor_report.py`, `graph_factory.py`, `rag/query_chain.py` — bumped `logger.warning` → `logger.error` so internal API failures and tool errors now surface in Sentry automatically
- [x] Confirmed `ingestion/pipeline.py`, `document_classifier.py`, and `backend/services/document_service.py` already used `logger.error`/`.exception` correctly — no change needed
- [x] QA verified: ingested 4 documents (2 blood tests, symptoms, supplements) as a fresh user, ran 6 different query types (trend analysis, symptom summary, supplement status, timeline, streaming), all correct with zero errors in logs

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

### Task 6.3 — Google OAuth ✅
- [x] Click "Continue with Google" → Google account picker appears
- [x] Select account → logged into app with correct email shown
- [x] Log out → log back in with Google → works without re-consent
- [x] Logged in with two different Google accounts in the same browser session → found and fixed a cross-account chat leak bug (see Phase 8 — `useChat` state wasn't resetting on account switch)
- [ ] Register a new email/password account, then log in with Google using same email → accounts linked, same user (not yet tested)

---

## Phase 7 — PostgreSQL and Qdrant auth ✅

**Why:** Both databases ran with no authentication. Postgres used `trust` mode (ignores passwords) and Qdrant had no API key.

### Task 7.1 — PostgreSQL: update docker-compose.yml ✅
- [x] Add `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` to the postgres service environment
- [x] Remove `POSTGRES_HOST_AUTH_METHOD: trust`
- [x] Renamed default Postgres user from `yakir` to `adminuser` (`backend/core/config.py`, `ai-agent/core/config.py`, `docker-compose.yml`, `eval/setup_and_run.py`, `backend/alembic.ini`)

### Task 7.2 — PostgreSQL: refactored to individual env vars (not a single DATABASE_URL) ✅
- [x] `backend/core/config.py` and `ai-agent/core/config.py`: replaced required `database_url: str` field with `postgres_host` / `postgres_port` / `postgres_user` / `postgres_password` / `postgres_db` (only `postgres_password` is required, others default to local-friendly values) plus a computed `database_url` property
- [x] `docker-compose.yml`: `migrate`/`backend`/`ai-agent` services now override `POSTGRES_HOST` + `POSTGRES_PASSWORD` instead of a full `DATABASE_URL` string
- [x] `backend/alembic/env.py`: now imports `settings.database_url` directly instead of reading a raw `DATABASE_URL` env var
- [x] Fixed a password leak — `backend/main.py` startup log used to print the full `database_url` (including password); now logs only host/port/db name
- [x] Add `POSTGRES_PASSWORD=<your-password>` to `backend/.env`, `ai-agent/.env`, and root `.env` (different values for dev vs. prod)

### Task 7.3 — Qdrant: update docker-compose.yml ✅
- [x] Add `QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}` to the qdrant service environment
- [x] Pass `QDRANT_API_KEY` through to the `ai-agent` service environment too

### Task 7.4 — Qdrant: update ai-agent code ✅
- [x] Add `qdrant_api_key: str = ""` to `ai-agent/core/config.py`
- [x] Pass `api_key=settings.qdrant_api_key` to `QdrantClient` in `ai-agent/rag/qdrant_client.py`
- [x] **Found and fixed a bug**: `QdrantClient` defaults to `https=True` whenever an `api_key` is set (assumes Qdrant Cloud) — broke ai-agent startup with `[SSL: WRONG_VERSION_NUMBER]` against our self-hosted, non-TLS Qdrant. Fixed with explicit `https=False`.
- [x] Add `QDRANT_API_KEY=<your-key>` to `ai-agent/.env` and root `.env`

### Task 7.5 — Wipe and recreate (local) ✅
```bash
docker compose down -v        # stops containers AND deletes all volumes (postgres + qdrant + uploads)
docker compose build
docker compose up -d          # recreates everything fresh with auth enabled
```
- [x] Ran locally — confirmed working

### Task 7.6 — Verify ✅ (local)
- [x] `docker compose logs migrate` — all 8 migrations ran successfully against `adminuser`-authenticated Postgres
- [x] `docker compose logs backend` — no database connection errors
- [x] `docker compose logs ai-agent` — no Qdrant connection errors after the `https=False` fix
- [x] Qdrant correctly rejects unauthenticated requests (`401 Must provide an API key`)
- [x] Registered a user, uploaded a document, ran a query — full pipeline works end-to-end
- [x] Backend + ai-agent test suites — zero regressions vs. established baseline

### Task 7.7 — Deploy to server ✅
- [x] Generated **separate** `POSTGRES_PASSWORD` and `QDRANT_API_KEY` values for production (different from local dev values)
- [x] Added to `backend/.env`, `ai-agent/.env`, and root `.env` on the server
- [x] Pushed to `main` — CI/CD deployed the code changes
- [x] Wiped and recreated volumes on the server with auth enabled
- [x] Verified Postgres auth — registered a new user and logged in successfully against `adminuser`-authenticated Postgres
- [x] Verified Qdrant auth — uploaded a journal-style document (not stored in any Postgres table), asked a question only answerable via semantic search, confirmed via logs that the `search_documents` tool hit Qdrant and returned the correct answer
- [x] Found and fixed a production session bug along the way — see "Session expiry reload-loop fix" below

---

## Phase 8 — Session expiry reload-loop fix ✅

**Symptom:** Visiting `https://healthsignal.yakirzaken.com/` triggered a continuous page-refresh loop in browsers with an existing (stale/invalid) session. Worked fine in incognito (no localStorage).

**Root cause:**
- The 401-handling logic in `frontend/src/api/backend.ts` (duplicated across `request()` and `sendQueryStream()`, plus a third copy in `admin.ts`) only removed the `hs_token` key on session expiry — never `hs_email` or the active-session key, unlike the proper `logout()` function in `AuthContext`.
- `App.tsx` calls `useChat(email ?? '')` **unconditionally**, before checking `isAuthenticated`. With a stale `email` still in localStorage, `useChat`'s data-fetch effect kept firing on every reload, regardless of whether the user was actually logged in.
- Each 401 response triggered a hard `window.location.reload()` — fragile under concurrent requests and prone to repeating instead of cleanly settling on the login screen.

**Fix:**
- [x] Added `frontend/src/api/sessionEvents.ts` — a small pub/sub bridge so plain API modules (outside React) can request a logout without touching `localStorage` or `window.location` directly
- [x] `backend.ts` and `admin.ts`: replaced manual `localStorage.removeItem` + `window.location.reload()` with `triggerSessionExpired()`
- [x] `AuthContext.tsx`: registers its existing, already-correct `logout()` (clears token + email + active session, updates React state) as the session-expired handler — no full-page reload needed at all
- [x] QA verified: seeded a stale invalid token + lingering email in localStorage, reloaded — app now settles cleanly on the login screen in one render, with all three localStorage keys (`hs_token`, `hs_email`, `hs_active_session_*`) correctly cleared

---

## Deferred / future

- Move uploaded files to Cloudflare R2 (decouples file storage from server disk)
- pg_dump cron job (if/when 1-day data loss becomes unacceptable with paying users)
- Apple Sign In
- Phase 9 — Uptime Robot (moved to Phase 2 above)
