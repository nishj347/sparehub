# SpareHub - Production Deployment Guide

This document provides complete instructions for deploying and operating SpareHub in production using Docker Compose.

---

## 1. Architecture Overview

```
[ Browser / Client ]
         │ (HTTPS :443)
         ▼
[ External Load Balancer / Reverse Proxy (Traefik, Cloudflare, AWS ALB) ]
         │ (HTTP :8080 with X-Forwarded-*)
         ▼
┌────────────────────────────────────────────────────────┐
│ SpareHub Docker Compose Production Stack               │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ web (Nginx Unprivileged, port 8080)              │  │
│  │ - Serves built React SPA (HTML/CSS/JS)           │  │
│  │ - Enforces CSP, HSTS, Nosniff, Frame-Options     │  │
│  │ - Proxies /api/ and /uploads/ to backend         │  │
│  └──────────┬───────────────────────────┬───────────┘  │
│             │                           │              │
│      /api/* │                  /uploads │              │
│             ▼                           ▼              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ backend (FastAPI + Uvicorn, port 8000 internal)  │  │
│  │ - Non-root execution (`appuser`)                 │  │
│  │ - 8MB body limit, rate-limiting & lockout        │  │
│  │ - Access to named volume: uploads                │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │ SQL connection                   │
│                     ▼                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ db (PostgreSQL 16 Alpine, port 5432 internal)    │  │
│  │ - Access to named volume: pgdata                 │  │
│  │ - Not published to host network                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ migrate (Alembic one-shot container)             │  │
│  │ - Runs `alembic upgrade head` before backend     │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites

- **Host Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 / RHEL 9 recommended) or Windows Server with Docker Desktop.
- **Docker Engine:** Version 20.10+ (tested on Docker 29.3+).
- **Docker Compose:** Version 2.0+ (Docker Compose v5+).
- **TLS Reverse Proxy:** Cloudflare, AWS ALB, Traefik, or Caddy terminating TLS in front of the host port `8080`.

---

## 3. First-Time Setup & Installation

### Step 3.1: Clone the Repository
```bash
git clone https://github.com/your-org/sparehub.git /opt/sparehub
cd /opt/sparehub
```

### Step 3.2: Create and Configure `.env.production`
Copy the template configuration:
```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Generate a secure 32+ character `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edit `.env.production` and configure:
1. `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.
2. `DATABASE_URL` matching the PostgreSQL credentials.
3. `SECRET_KEY` set to the generated string.
4. `CORS_ORIGINS` set to your production domain(s) (e.g. `https://spareparts.yourcompany.com`).
5. `ALLOWED_HOSTS` set to your domain name and internal container hosts.
6. `APP_TIMEZONE` set to your company timezone (e.g. `Asia/Kolkata` or `UTC`).

> [!IMPORTANT]
> Never set or configure `SEED_DEFAULT_PASSWORD` in `.env.production`. Production must start with an empty database.

### Step 3.3: Build and Launch the Stack
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Verify that all services are healthy and running:
```bash
docker compose -f docker-compose.prod.yml ps
```
The output should indicate:
- `sparehub_prod_db`: healthy
- `sparehub_prod_migrate`: exited 0
- `sparehub_prod_backend`: healthy
- `sparehub_prod_web`: healthy, port `8080:8080`

### Step 3.4: Create the Initial Store Administrator
Run the interactive user creation CLI inside the backend container:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend python -m app.scripts.create_admin
```
Provide the Employee ID, Full Name, Email, Location Code, and secure initial password.

### Step 3.5: Bulk Import Employees (Optional)
If you have a CSV roster of employees:
```bash
# First test in dry-run mode
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm \
  -v $(pwd)/users.csv:/app/users.csv \
  backend python -m app.scripts.import_users /app/users.csv --dry-run

# Commit import and save temporary passwords
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm \
  -v $(pwd)/users.csv:/app/users.csv \
  -v $(pwd)/backups:/app/backups \
  backend python -m app.scripts.import_users /app/users.csv --output /app/backups/imported_passwords.csv
```

---

## 4. TLS & Reverse Proxy Configuration

SpareHub expects TLS termination at an upstream load balancer or front proxy. Ensure the proxy forwards:
- `X-Forwarded-For: $proxy_add_x_forwarded_for`
- `X-Forwarded-Proto: https`
- `X-Forwarded-Host: $host`
- `Host: $host`

### Example Nginx Frontend Proxy Block:
```nginx
server {
    listen 443 ssl http2;
    server_name spareparts.yourcompany.com;

    ssl_certificate /etc/ssl/certs/spareparts.crt;
    ssl_certificate_key /etc/ssl/private/spareparts.key;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

---

## 5. Operations & Maintenance

### 5.1 Viewing Application Logs
```bash
# View backend logs
docker compose -f docker-compose.prod.yml logs -f backend

# View Nginx access/error logs
docker compose -f docker-compose.prod.yml logs -f web

# View database logs
docker compose -f docker-compose.prod.yml logs -f db
```

### 5.2 Resetting a Locked User Account
If an employee or admin triggers the login brute-force lockout (5 consecutive failed attempts):
```bash
docker compose -f docker-compose.prod.yml exec db psql -U sparehub_admin -d sparehub_prod -c \
  "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE employee_id = 'EMP001';"
```

### 5.3 Automated Backups & Disaster Recovery
- Backup script: `./scripts/backup.sh` (Linux/macOS) or `.\scripts\backup.ps1` (Windows).
- Schedule backups daily at 02:00 via cron or Task Scheduler.
- Restore instructions: refer to [restore.md](scripts/restore.md).

---

## 6. Upgrades & Migration Procedure

1. **Back up the current state first:**
   ```bash
   ./scripts/backup.sh
   ```
2. **Pull the latest release:**
   ```bash
   git pull origin master
   ```
3. **Rebuild images and apply migrations:**
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
   ```
   The `migrate` service will automatically run `alembic upgrade head` before the updated `backend` containers start.
4. **Verify system health:**
   ```bash
   curl -fsS http://localhost:8080/healthz
   curl -fsS http://localhost:8080/api/health
   curl -fsS http://localhost:8080/api/health/db
   ```

### Rollback Procedure
If a migration needs to be rolled back:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic downgrade -1
docker compose -f docker-compose.prod.yml --env-file .env.production restart backend
```

---

## 7. Known Limitations & Recommended Next Steps

| Limitation | Current Architecture | Recommended Production Enhancement |
|:---|:---|:---|
| **High Availability** | Single host with Docker Compose | Multi-node cluster with container orchestration (ECS / Nomad / Kubernetes) |
| **Media Storage** | Local Docker volume (`uploads`) | Cloud object storage (AWS S3, Google Cloud Storage, Cloudflare R2) via S3 SDK |
| **Notifications** | In-app notification polling | Email delivery (SMTP / Amazon SES / SendGrid) and Slack/Teams webhooks |
| **Authentication** | Username/Password with Argon2id | Enterprise SSO via OIDC / SAML 2.0 (Okta, Azure AD / Microsoft Entra ID) |
| **Password Management** | Admin resets password | Self-service password reset via verified email link |
| **Audit Logs** | PostgreSQL activity ledger table | Exportable compliance audit logs to external SIEM (Splunk, Datadog) |

