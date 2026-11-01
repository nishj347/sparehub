# SpareHub - Production Go-Live Verification Checklist

Before taking SpareHub live to real end-users, complete and check off each item on this list.

---

## 1. Secrets & Credentials Security
- [ ] **Strong `SECRET_KEY` configured:** Set to a cryptographically secure random token (>=32 characters). Generated via `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Default or placeholder values will cause FastAPI to abort on startup.
- [ ] **Database password rotated:** `POSTGRES_PASSWORD` is unique, strong (>=24 characters), and never committed to version control.
- [ ] **Zero secrets in source control:** `.env.production` is untracked by Git (`.gitignore` verified). No secrets present in Docker images or build logs.
- [ ] **Seed data NOT loaded:** `SEED_DEFAULT_PASSWORD` is omitted or empty. Prototype demo accounts (`EMP001` with `Password123!`) do NOT exist in the production database.

---

## 2. Infrastructure & Network Isolation
- [ ] **Database port 5432 isolated:** `docker-compose.prod.yml` does NOT expose or publish port 5432 to the host network. PostgreSQL is accessible ONLY within the internal bridge network.
- [ ] **Backend port 8000 isolated:** FastAPI runs on internal port 8000. Only the Nginx `web` container (port 8080) is published.
- [ ] **HTTPS / TLS configured:** Upstream proxy (Cloudflare, Caddy, AWS ALB, Traefik) handles TLS certificate termination and redirects HTTP to HTTPS.
- [ ] **Host header validation:** `ALLOWED_HOSTS` configured in `.env.production` matching your production domain name(s).
- [ ] **CORS restrictions:** `CORS_ORIGINS` explicitly set to `https://spareparts.yourcompany.com` without wildcards.
- [ ] **Security headers active:** Verified with `curl -I https://spareparts.yourcompany.com`:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy: camera=(self), geolocation=(), microphone=()`
  - `Content-Security-Policy: default-src 'self' ...`

---

## 3. Application Hardening & Verification
- [ ] **Interactive API Docs disabled:** Verified that `GET /docs`, `GET /redoc`, and `GET /openapi.json` return HTTP 404 in production mode.
- [ ] **Login brute-force lockout verified:** 5 consecutive incorrect password attempts lock the account for 15 minutes (HTTP 429 + `Retry-After: 900`).
- [ ] **Non-root container execution:** Backend runs under unprivileged `appuser` (UID 10001); Nginx runs under `nginxinc/nginx-unprivileged` (UID 101).
- [ ] **Single Alembic migration head:** Verified with `alembic heads` (`b2c3d4e5f6a7 (head)`).
- [ ] **Automated test suite passing:** All 119 unit/integration/concurrency tests pass against `sparehub_test`.
- [ ] **Concurrency & row-locking verified:** 5 consecutive multi-threaded concurrent issue test runs passed without inventory drift or deadlock.

---

## 4. Disaster Recovery & Operations
- [ ] **First administrator created:** Created via `docker compose ... run --rm backend python -m app.scripts.create_admin`.
- [ ] **Disaster recovery restore verified:** Tested backup and restore cycle into a scratch database (`sparehub_restore_test`) using `scripts/restore.md`.
- [ ] **Automated daily backups scheduled:** Crontab or Windows Task Scheduler job active with 14-day retention cycle.
- [ ] **Data persistence verified:** Restarting the stack preserves PostgreSQL database tables and media uploads.

---

## 5. Vulnerability & Code Quality Scans
- [ ] **pip-audit reviewed:** Python dependencies scanned.
  - *Status:* 25 CVEs reported against pinned prototype versions in `requirements.txt` (including `pyjwt==2.10.1`, `starlette==0.41.3`, `python-dotenv==1.0.1`).
  - *Recommendation:* Upgrade to `pyjwt>=2.15.0` and `starlette>=1.3.1` in the next scheduled dependency maintenance release.
- [ ] **npm audit reviewed:** Production frontend dependencies scanned (`npm audit --omit=dev`).
- [ ] **Python syntax & compilation:** `python -m compileall app` and `python -m pyflakes app` passed without errors.
- [ ] **Frontend bundle verified:** Zero `localhost` references and zero `.map` sourcemap files present in `frontend/dist`.

