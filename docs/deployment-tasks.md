# Deployment Tasks — Health Signal

## Status: Phase 3 in progress

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
- [ ] Create `/opt/health-signal/.env.backend` with production values
- [ ] Create `/opt/health-signal/.env.ai-agent` with production values
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

## Phase 8 — Answer Quality (Post-launch)

Systematically measure and improve the accuracy of agent answers using an eval dataset.

### Task 8.1 — Build eval dataset

Create a golden dataset of questions with expected answers, covering all agent routes.
Store in `eval/dataset.json` (or extend the existing eval dataset if one exists).

- [ ] Write ~5 questions per route: `lab_analysis`, `pattern_detection`, `timeline`, `rag`
- [ ] For each question record:
  - `question` — exact text to send
  - `expected_answer` — the correct factual answer (numbers, dates, names)
  - `route` — which agent should handle it
  - `key_facts` — list of specific facts the answer must contain (e.g. `["11 µg/L", "February 2024"]`)
- [ ] Use the demo data files as the source of truth for expected answers
- [ ] Include edge cases: questions with specific dates, dose changes, cross-document reasoning

### Task 8.2 — Run eval and record baseline

- [ ] Upload all demo data files to the app (fresh session)
- [ ] Send each question from the dataset and record the actual answer
- [ ] For each question mark: Pass / Fail / Partial (based on whether key_facts are present)
- [ ] Record the route the supervisor chose (check logs) — flag misroutes
- [ ] Calculate baseline score: `passed / total`

### Task 8.3 — Fix and iterate

For each failing question, diagnose the root cause and fix it:

| Root cause | Fix |
|---|---|
| Wrong route (e.g. supplement dose → lab_analysis) | Update `CLASSIFY_PROMPT` in `supervisor.py` with better examples |
| Correct route, wrong data from DB | Check DB contents, fix ingestion extractor prompt |
| Correct data, LLM picks wrong value | Add precision instruction to the agent's system prompt |
| Missing context (answer spans multiple docs) | Increase `TOP_K` in retriever or improve chunking |
| Hallucination with no data | Check if data was ingested; improve "no data" guardrails |

- [ ] Fix one issue at a time, re-run the affected questions, verify improvement
- [ ] Re-run full eval after each batch of fixes — track score over iterations
- [ ] Target: ≥ 80% Pass on the golden dataset before considering quality stable

### Task 8.4 — Automate eval (optional)

- [ ] Write a script `eval/run_eval.py` that sends each question via the API and checks key_facts automatically
- [ ] Add to CI or run manually before each major change to catch regressions

---

## Phase 9 — Monitoring (Future)

Not a blocker for launch. Add after the app is live.

- [ ] Decide on monitoring tool (Uptime Robot free tier for uptime alerts, or self-hosted)
- [ ] Set up uptime monitoring for `healthsignal.yakirzaken.com`
- [ ] Set up basic alerting (email on downtime)
- [ ] Consider adding `pg_dump` cron job for point-in-time PostgreSQL recovery

---

## Summary

| Phase | Description | Effort |
|-------|-------------|--------|
| 1 | Code changes (embedder + build) | Medium |
| 2 | Dockerize all services | Medium |
| 3 | Provision Hetzner with Terraform | Small |
| 4 | Domain, DNS, TLS | Small |
| 5 | Server setup + first deploy | Small |
| 6 | GitHub Actions CI/CD | Small |
| 7 | Smoke test + launch | Small |
| 8 | Answer quality — eval & fix loop | Medium |
| 9 | Monitoring | Future |
