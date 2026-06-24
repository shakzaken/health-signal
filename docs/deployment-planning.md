# Deployment Planning — Health Signal

## Status: Planning

---

## 1. Goals

- Deploy Health Signal to production
- Minimize monthly infrastructure cost
- Keep the GitHub repo public (portfolio value is working — recruiters are engaging)
- Potential future: paid product with real users

---

## 2. Infrastructure Decisions

### Cloud Provider — Hetzner

- **Decision:** Hetzner (Germany data center)
- **Why:** 2-3x cheaper than DigitalOcean for equivalent specs; good Terraform support via official `hetznercloud/hcloud` provider
- **Latency from Israel:** ~60-70ms to Germany — acceptable for this app; real bottleneck is OpenAI API latency, not server location
- **IaC:** Terraform with the official Hetzner provider

### Server — Single CAX21

- **Decision:** One CAX21 instance running all services
- **Specs:** 4 vCPU (ARM), 8GB RAM, 80GB SSD NVMe
- **Cost:** ~€8.49/month (~$9.40)
- **Why single server:** Removing the local embedding model (see below) drops total RAM usage to ~2GB, making 8GB very comfortable for all services combined
- **Runs:** Backend (FastAPI), AI-Agent (FastAPI), Qdrant, PostgreSQL (self-hosted)

### Embedding Model — Qwen3-Embedding via OpenRouter

- **Decision:** Replace local FastEmbed (`intfloat/multilingual-e5-large`) with Qwen3-Embedding via OpenRouter API
- **Why:**
  - Qwen3-Embedding is #1 on MTEB multilingual leaderboard (score 70.58) — better than the current model (~62)
  - Strong Hebrew / non-Latin script support — critical for Clalit PDFs
  - Available via OpenRouter (same API key as LLM calls, one bill)
  - Removes ~500-800MB RAM from the AI-agent (no local model loaded), enabling the CAX21 downsize
- **API cost:** ~$0.06/month at early-stage usage (negligible)
- **Note:** All existing Qdrant vectors must be re-embedded on switch (vector space changes)

### Domain — yakirzaken.com via Cloudflare Registrar

- **Decision:** Buy `yakirzaken.com` as a personal brand domain; serve the app on `healthsignal.yakirzaken.com`
- **Registrar:** Cloudflare Registrar — $10.11/year, at-cost, no renewal markup, free WHOIS privacy
- **Subdomains:** Free — just DNS A records pointing to the Hetzner floating IP
- **DNS:** Cloudflare DNS + Proxy (free CDN, DDoS protection, hides server IP)
- **Future projects:** any new project gets its own subdomain at no extra cost
- **Nginx routing:** server block per subdomain — `healthsignal.yakirzaken.com` → backend :8000

### TLS / HTTPS — Cloudflare Origin Certificate

- **Decision:** Cloudflare Origin Certificate for Nginx, Cloudflare SSL mode set to Full (Strict)
- **Why not Let's Encrypt:** Already committed to Cloudflare proxy — Origin Certificate is valid for 15 years, zero renewal maintenance, issued directly from the Cloudflare dashboard
- **Two TLS layers:**
  - User → Cloudflare: handled automatically by Cloudflare (free, nothing to configure)
  - Cloudflare → Nginx: secured by the Origin Certificate
- **Setup steps:**
  1. Cloudflare dashboard → SSL/TLS → set mode to **Full (Strict)**
  2. Cloudflare dashboard → Origin Server → create certificate → download `.pem` and `.key`
  3. Mount both files into the Nginx container
  4. Configure Nginx server block to use them

### Frontend — Served by Nginx on the same server

- **Decision:** React build output served as static files by Nginx on the CAX21
- **Why:** Already running Nginx — no extra service, no extra cost, no extra complexity

### CI/CD — GitHub Actions

- **Decision:** GitHub Actions deploys automatically on push to `main`
- **Why:** Public repo = unlimited free minutes; deploy is just `git push`
- **Flow:** push to `main` → GitHub Actions SSHes into Hetzner → `git pull` → `docker compose up -d --build`
- **GitHub secrets needed:** `HETZNER_HOST` (server IP), `HETZNER_SSH_KEY` (private SSH key)
- **Downtime:** brief container restart on each deploy — acceptable at early stage

### Secrets — Manual `.env` files on server

- **Decision:** `.env` files created manually on the server once via SSH; never committed to git
- **Files:** `.env.backend` and `.env.ai-agent` in `/opt/health-signal/`
- **Docker Compose:** each service references its file via `env_file:`
- **Service networking:** inside Docker Compose, services communicate by service name (e.g. `QDRANT_HOST=qdrant`, `BACKEND_URL=http://backend:8000`)
- **Backup:** all production secrets stored in a password manager as a secure note
- **Future:** when CI/CD matures, migrate secrets to GitHub Actions secrets and write `.env` files automatically on deploy

### File Storage — Local disk on CAX21

- 80GB included on CAX21 — sufficient for early production
- If uploads grow: add Hetzner Block Storage at €0.057/GB/month

### Vector Store — Qdrant (self-hosted on CAX21)

- Self-hosted on the same server
- Qdrant Cloud free tier (1GB RAM, 4GB disk) as fallback option if memory becomes constrained

### Deployment Method — Docker Compose

- **Decision:** All services run in Docker containers managed by Docker Compose
- **Services:** backend, AI-agent, PostgreSQL, Qdrant, Nginx — all in one `docker-compose.yml`
- **Volumes:** Docker named volumes mapped to the Hetzner disk for data persistence (PostgreSQL data, Qdrant data, uploaded PDFs)
- **Why not bare processes:** Isolation, easy restarts, consistent environments, simpler deploys (`docker compose up -d --build`)
- **Why not Kubernetes:** Single server — no need for multi-node orchestration

### Backups — Hetzner Server Backups

- **Decision:** Enable Hetzner's built-in server backup feature
- **Cost:** 20% of server cost = **€1.70/month**
- **What it covers:** Full disk snapshot — PostgreSQL data, Qdrant vectors, uploaded PDFs, all in one
- **How:** One checkbox in the Hetzner dashboard — automatic, no scripting required
- **Why Qdrant is also critical:** Qdrant is NOT fully reconstructable — users may input text directly via chat (not only via file upload), so Qdrant may contain data with no corresponding file on disk
- **Future:** When real paying users exist, add a `pg_dump` cron job on top for database-level point-in-time recovery

---

## 3. Cost Summary

| Item | Cost/month |
|------|-----------|
| Hetzner CAX21 | €8.49 (~$9.40) |
| Hetzner Floating IP | €1.19 (~$1.30) |
| Hetzner Server Backups | €1.70 (~$1.90) |
| Qwen3-Embedding API (OpenRouter) | ~$0.06 |
| Domain `yakirzaken.com` (Cloudflare) | $0.84 ($10.11/year) |
| **Total** | **~$13.50/month** |

---

## 4. Architecture Changes Required

| Change | Component | Notes |
|--------|-----------|-------|
| Replace `Embedder` class | `ai-agent/ingestion/embedder.py` | Switch from FastEmbed to Qwen3-Embedding via OpenRouter |
| Re-embed all documents | Qdrant collection | Required when switching embedding model |
| Containerize all services | All | Docker Compose — one `docker-compose.yml` for all services |
| Nginx reverse proxy | Server | Route traffic to backend/frontend, runs in Docker |
| TLS certificate | Cloudflare dashboard | Generate Origin Certificate, mount into Nginx container, set SSL mode to Full (Strict) |
| Environment secrets | All | Production `.env` files created manually on server via SSH, never committed to git |
| Enable server backups | Hetzner dashboard | One checkbox — €1.70/month, covers everything |
| Database migrations | GitHub Actions deploy script | `docker compose run --rm backend alembic upgrade head` before `docker compose up -d` |
| GitHub Actions workflow | `.github/workflows/deploy.yml` | build → migrate → up on push to `main` |
| CORS | `backend/core/config.py` | No changes needed — frontend and backend share same domain in production |

---

## 5. Open Decisions

- [ ] Buy `yakirzaken.com` on Cloudflare Registrar and enable Cloudflare Proxy
- [ ] Monitoring / alerting strategy
- [x] Database migrations — run via GitHub Actions deploy script before containers restart
- [x] CORS — no changes needed; frontend and backend share the same domain in production so CORS doesn't apply

---

## 6. GitHub Repo Strategy

- **Decision:** Keep public for now
- **Why:** Recruiters are already finding and engaging with the project through the public repo — that visibility is an asset
- **When to go private:** When the product has paying customers worth protecting
- **Note:** GitHub allows switching public → private at any time in Settings
