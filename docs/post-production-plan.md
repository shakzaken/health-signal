# Next Phases Planning — Health Signal

## Status: Discussion in progress

---

## Context

App is live at https://healthsignal.yakirzaken.com. All deployment phases (1–6) complete. Smoke test (Phase 7) passed — all features working including Hebrew language support.

Current state:
- CX33 server (4 vCPU, 8GB RAM, 80GB SSD, Nuremberg)
- CI/CD via GitHub Actions on push to `main`
- Eval framework in place; test 001 at 20/20, test 002 at 16/21 (5 routing WARNs)

---

## Known open items (from deployment phases)

- **Phase 8 — Answer quality**: Fix 5 supervisor routing bugs in `ai-agent/agents/supervisor.py` (`CLASSIFY_PROMPT`); all 5 failures route to `lab_analysis` instead of `pattern_detection`, `timeline`, or `rag`
- **Phase 9 — Monitoring**: Uptime Robot for healthsignal.yakirzaken.com
- **Task 3.2** — Enable Hetzner server backups (one checkbox, €1.70/month) — NOT YET DONE
- **Task 7.2** — Update README and LinkedIn with live URL

---

## Discussions

### Monitoring

**Uptime and error tracking**
- **Uptime Robot** — pings the app every 5 minutes, sends email alert on downtime. No code changes needed.
- **Sentry** — captures exceptions with full stack traces (user, endpoint, error). Free tier: 5,000 errors/month. Add Python SDK to backend and JS SDK to frontend (~3 lines each).

**User activity — admin panel**
- Track per-user query count, ingestion count, and totals
- Data lives in existing DB — add a `usage_events` table, record events as they happen in the backend
- Build a protected `/admin` route in the React frontend that reads from a protected API endpoint
- Backend check: `current_user.email == ADMIN_EMAIL` (env var)

**Admin panel contents**
- Summary cards: total users, total queries, total ingestions, active users (last 7 and 30 days)
- Users table: email, registration date, last login, documents ingested, queries sent, verified status
- New users over time (daily/weekly)
- Storage used (total disk space consumed by uploads)

**Admin actions**
- Create user form: email + password + "Test / automation user" checkbox → creates user as already verified (skips email confirmation)
- Verify user button: manually approve an unverified user

**Test / automation user flag**
- `is_test_user` boolean column on the users table (default `false`)
- All stats queries filter out `is_test_user = true` — test users are invisible to totals and per-user stats
- Eval users (`eval-001@healthsignal.dev`, `smoketest@healthsignal.dev`, etc.) are created via the admin panel with this flag set

**Admin panel security — two independent layers**
- **Layer 1 — Cloudflare Access (Zero Trust)**: protects `/admin` path at the network edge. Requires Google login (your account only) before the request reaches the server. Free for up to 50 users. ~20 min setup in Cloudflare dashboard, zero code changes.
- **Layer 2 — App JWT**: backend verifies valid JWT + email matches `ADMIN_EMAIL`. Even if Layer 1 is bypassed, backend rejects the request.
- Attacker would need to compromise your Google account AND have a valid app JWT — genuinely strong.

---

### Backups

- **Decision: Hetzner server backups only** — one checkbox in the Hetzner dashboard, ~€1.70/month
- Hetzner takes a full daily snapshot of the server disk — covers PostgreSQL, Qdrant, and uploaded files in one shot
- Keeps last 3 snapshots; restore rolls the entire server back to that point (DB + Qdrant + files together)
- 1 day of potential data loss is acceptable at this stage
- pg_dump deferred — adds complexity for a problem that doesn't exist yet; revisit if/when paying users require stricter SLA

**Action required:** Enable in Hetzner dashboard (not yet done)

---

### Auth improvements

**Google OAuth**
- Add Google login as an alternative to email/password
- Google only for now — covers the majority of users; Apple and others deferred
- Facebook skipped — privacy concerns are especially problematic for a health app

**Password rules**
- Current: no rules enforced
- Decision: Option C — min 8 characters + at least 1 number + at least 1 uppercase letter
- Example valid password: `Yakir123`
- Implemented via Pydantic validation on the register endpoint

**Email confirmation**
- Flow: user registers → backend generates a secure token → sends a verification email → user clicks link → account activated
- Until verified: user cannot log in
- Token expires after 24 hours
- Email provider: **Resend** (free tier: 3,000 emails/month, 100/day — sufficient for early stage)
- Sending domain: `noreply@yakirzaken.com` (DNS records added to Cloudflare — SPF, DKIM)
