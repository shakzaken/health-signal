# Deployment Tasks — Health Signal

## Status: Phase 8 in progress (eval fixes), Phase 3–7 pending

---

## Phase 1 — Code Changes ✅

Changes to the codebase required before containerizing.

### Task 1.1 — Replace Embedder with Qwen3 via OpenRouter ✅

- [x] Add OpenRouter API key to `ai-agent` config (`core/config.py`)
- [x] Rewrite `ai-agent/ingestion/embedder.py` — replace FastEmbed with async OpenRouter Qwen3-Embedding-8B
- [x] Update `ai-agent/rag/retriever.py` — ensure query embedding uses the same new Embedder
- [x] Remove `fastembed` from `ai-agent/pyproject.toml`
- [x] Test ingestion and query — working end-to-end in Docker

### Task 1.2 — Verify CORS ✅

- [x] Confirmed `ENVIRONMENT=production` disables CORS middleware — no changes needed

### Task 1.3 — Frontend production build ✅

- [x] `VITE_BACKEND_URL=""` (empty) baked into nginx image at build time — relative URLs work behind nginx proxy

---

## Phase 2 — Dockerize ✅

Write all Docker and Compose configuration.

### Task 2.1 — Dockerfiles ✅

- [x] Write `backend/Dockerfile`
- [x] Write `ai-agent/Dockerfile`
- [x] Write `frontend/Dockerfile` (multi-stage: node build → nginx serve)

### Task 2.2 — Nginx configuration ✅

- [x] Write `nginx/nginx.local.conf` — HTTP only, for local Docker testing
- [x] Write `nginx/nginx.conf` — production TLS with Cloudflare Origin Certificate, HTTP→HTTPS redirect

### Task 2.3 — Docker Compose ✅

- [x] Write `docker-compose.yml` with services: postgres, qdrant, migrate, backend, ai-agent, nginx
- [x] `migrate` service runs `alembic upgrade head` before backend starts
- [x] Named volumes: `postgres_data`, `qdrant_data`, `uploads`
- [x] Added initial schema migration (`0000_initial_schema.py`) — was missing

### Task 2.4 — Local end-to-end test ✅

- [x] All services start without errors
- [x] Upload, chat, and report flows working
- [x] Several bugs fixed: nullable document_type, duplicate upload on failure, supplement dose history

---

## Phase 3 — Infrastructure

Provision the Hetzner server with Terraform.

### Task 3.1 — Terraform setup ✅

- [x] Create `terraform/` directory in repo root
- [x] Write `terraform/main.tf` with:
  - Hetzner provider (`hetznercloud/hcloud`)
  - CAX21 server (ARM, 8GB RAM, Falkenstein Germany) with Docker installed via user_data
  - Floating IP attached to the server
  - Firewall: allow 22 (SSH), 80 (HTTP), 443 (HTTPS), block everything else
  - SSH key resource
- [x] Write `terraform/variables.tf` for API token and SSH key
- [x] Write `terraform/outputs.tf` — prints floating IP and SSH command after apply
- [ ] Create `terraform/terraform.tfvars` from the example file (not committed — contains secrets)
- [ ] Run `terraform init && terraform plan`
- [ ] Run `terraform apply` — server is created

### Task 3.2 — Hetzner dashboard

- [ ] Enable server backups (one checkbox, adds €1.70/month)
- [ ] Note the Floating IP address — needed for DNS

---

## Phase 4 — Domain & DNS

### Task 4.1 — Buy domain

- [ ] Register `yakirzaken.com` on [Cloudflare Registrar](https://domains.cloudflare.com)

### Task 4.2 — DNS records

- [ ] In Cloudflare DNS, add A record: `healthsignal.yakirzaken.com` → Hetzner Floating IP (proxy enabled)
- [ ] In Cloudflare DNS, add A record: `yakirzaken.com` → Hetzner Floating IP (proxy enabled, for future portfolio)
- [ ] Set Cloudflare SSL/TLS mode to **Full (Strict)**

### Task 4.3 — TLS certificate

- [ ] In Cloudflare dashboard → SSL/TLS → Origin Server → Create certificate
- [ ] Download `origin.pem` and `origin.key`
- [ ] Store copies in password manager

---

## Phase 5 — Server Setup

One-time manual setup on the Hetzner server.

### Task 5.1 — Install dependencies

- [ ] SSH into server: `ssh root@<floating-ip>`
- [ ] Update system: `apt update && apt upgrade -y`
- [ ] Install Docker: follow official Docker docs for Ubuntu
- [ ] Install Docker Compose plugin: `apt install docker-compose-plugin`
- [ ] Verify: `docker --version` and `docker compose version`

### Task 5.2 — Clone repo and configure

- [ ] Clone repo: `git clone <repo-url> /opt/health-signal`
- [ ] Create `/opt/health-signal/backend/.env` with production values
- [ ] Create `/opt/health-signal/ai-agent/.env` with production values
- [ ] Save both `.env` files in password manager as backup
- [ ] Create `/opt/health-signal/nginx/certs/` directory
- [ ] Upload `origin.pem` and `origin.key` to `/opt/health-signal/nginx/certs/`

### Task 5.3 — First deploy

- [ ] `cd /opt/health-signal`
- [ ] `docker compose build`
- [ ] `docker compose run --rm backend alembic upgrade head` — run migrations
- [ ] `docker compose up -d` — start all services
- [ ] `docker compose ps` — verify all containers are running
- [ ] `docker compose logs backend` — check for startup errors
- [ ] Open `https://healthsignal.yakirzaken.com` and verify the app loads

---

## Phase 6 — CI/CD

Automate future deploys via GitHub Actions.

### Task 6.1 — GitHub secrets

- [ ] In GitHub repo → Settings → Secrets → Actions, add:
  - `HETZNER_HOST` — Floating IP address
  - `HETZNER_SSH_KEY` — private SSH key content

### Task 6.2 — GitHub Actions workflow

- [ ] Create `.github/workflows/deploy.yml` with steps:
  1. Trigger on push to `main`
  2. SSH into server
  3. `git pull`
  4. `docker compose build`
  5. `docker compose run --rm backend alembic upgrade head`
  6. `docker compose up -d`
- [ ] Push to `main` and verify the workflow runs successfully in GitHub Actions tab
- [ ] Verify the new version is live at `healthsignal.yakirzaken.com`

---

## Phase 7 — Smoke Test & Launch

### Task 7.1 — Full end-to-end verification

- [ ] Register a new user
- [ ] Upload a PDF document — verify processing completes
- [ ] Ask a question in chat — verify streaming response and sources
- [ ] Generate a doctor report — verify report is generated
- [ ] Test Hebrew query — verify response is in Hebrew
- [ ] Check all containers are healthy: `docker compose ps`

### Task 7.2 — Launch

- [ ] Update LinkedIn post with live URL
- [ ] Update GitHub repo README with live URL
- [ ] Update `docs/deployment-planning.md` status to `Live`

---

## Phase 8 — Answer Quality (Eval)

Systematically measure and improve the accuracy of agent answers.

### Task 8.1 — Eval framework ✅

- [x] LLM-as-judge eval framework with versioned test directories (`eval/tests/NNN/`)
- [x] Per-test data directories (`eval/tests/NNN/data/`) and per-test eval users (`eval-NNN@healthsignal.dev`)
- [x] `eval/setup_and_run.py` — registers/logs in as per-test user, uploads data, runs eval, generates report
- [x] `ai-agent/eval/run_evals.py` — `--dataset` flag to load per-test `dataset.json`
- [x] `eval/generate_report.py` — markdown report with scores, root cause analysis, recommendations

### Task 8.2 — Test 001 (Maya's data) ✅

- [x] Created `eval/tests/001/data/` — Maya's demo health documents
- [x] Created `eval/tests/001/dataset.json` — 20 eval cases
- [x] Baseline: **18/20 PASS** → iterated → **20/20 PASS**
- [x] Fixed `lab_01`: `fetch_lab_results` now sorted chronologically + ABNORMAL HISTORY SUMMARY section
- [x] Fixed `timeline_01`: added month-by-month chronological narrative instruction

### Task 8.3 — Test 002 (Daniel's data) — in progress

- [x] Created `eval/tests/002/data/` — Daniel's health documents (6 files: labs × 3, symptoms × 2, supplements × 1)
- [x] Created `eval/tests/002/dataset.json` — 21 eval cases covering lab, pattern, timeline, rag, safety
- [x] Current result: **16/21 PASS, 5 WARN, 0 FAIL**

**Completed fixes:**
- [x] Architectural fix: `search_documents` tool now uses `Retriever` directly instead of HTTP self-call to avoid recursive supervisor routing
- [x] Added `search_documents` to `TimelineAgent` — diary content was unreachable for subjective milestone questions
- [x] `TimelineAgent` and `PatternDetectionAgent` now constructed per-request (user_id is required at construction time for search_documents)
- [x] Removed temporary `/rag/search` endpoint (was intermediate fix, now obsolete)
- [x] Fixed `dataset.json` expected keywords for `rag_01` and `rag_03` to match actual document content
- [x] Added `scripts/qdrant_cleanup.py` (gitignored) — maintenance tool to delete orphaned Qdrant chunks by document_id, user_id, or email

**Remaining 5 WARNs — all routing issues (supervisor CLASSIFY_PROMPT):**

| Case | Question | Actual route | Expected route |
|------|----------|-------------|----------------|
| pattern_03 | "What happened during intense work in October?" | lab_analysis | pattern_detection |
| pattern_04 | "What health changes around the lifestyle changes?" | lab_analysis | pattern_detection |
| timeline_01 | "Give me a chronological summary of my health in 2024" | lab_analysis | timeline |
| timeline_04 | "When did Daniel's energy levels start improving?" | lab_analysis | timeline |
| rag_01 | "Why did Daniel start taking selenium?" | lab_analysis | rag |

- [ ] Fix `CLASSIFY_PROMPT` in `supervisor.py` to correctly route the 5 failing cases
- [ ] Re-run test 002 and verify improvement
- [ ] Re-run test 001 to confirm no regressions

### Task 8.4 — Test 003+ (future)

- [ ] Create additional test datasets with different user profiles and edge cases
- [ ] Target: ≥ 90% pass rate across all test suites before considering quality stable

---

## Phase 9 — Monitoring (Post-launch)

Not a blocker for launch. Add after the app is live.

- [ ] Set up uptime monitoring for `healthsignal.yakirzaken.com` (Uptime Robot free tier)
- [ ] Set up email alerting on downtime
- [ ] Consider adding `pg_dump` cron job for point-in-time PostgreSQL recovery

---

## Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Code changes (embedder + build) | ✅ Done |
| 2 | Dockerize all services | ✅ Done |
| 3 | Provision Hetzner with Terraform | 🔲 Pending |
| 4 | Domain, DNS, TLS | 🔲 Pending |
| 5 | Server setup + first deploy | 🔲 Pending |
| 6 | GitHub Actions CI/CD | 🔲 Pending |
| 7 | Smoke test + launch | 🔲 Pending |
| 8 | Answer quality — eval & fix loop | 🔄 In progress (16/21 on test 002) |
| 9 | Monitoring | 🔲 Post-launch |
