# SpareHub - Free-Tier Deployment Guide (Vercel + Render + Neon)

This guide walks you through deploying SpareHub entirely within generous free tiers:
- **Database:** [Neon](https://neon.tech) Serverless PostgreSQL (Free Tier)
- **Backend API:** [Render](https://render.com) Docker Web Service (Free Tier)
- **Frontend SPA:** [Vercel](https://vercel.com) Static Vite Build (Free Tier)

Estimated setup time: **15–20 minutes**.

---

## Architecture Overview

```
[ Browser Client ]
        │ (HTTPS)
        ▼
[ Vercel Edge CDN (Frontend SPA) ]
  - Serves static Vite HTML / CSS / JS bundle
  - Rewrites /api/* and /uploads/* to Render backend
        │ (HTTPS Server-to-Server Proxy)
        ▼
[ Render Web Service (FastAPI Docker) ]
  - Automatically runs `alembic upgrade head` on startup
  - Serves REST API on port 8000
        │ (Encrypted TLS connection with sslmode=require)
        ▼
[ Neon Serverless PostgreSQL ]
  - Auto-scaling / auto-suspending managed Postgres
```

---

## Step 1: Set Up Database on Neon

1. Sign up or log in to [Neon](https://console.neon.tech).
2. Click **Create Project**:
   - **Project Name:** `sparehub` (or your preferred name)
   - **Postgres Version:** 16 (default)
   - **Region:** Choose a region close to your Render deployment (e.g., US East / Ohio or Frankfurt).
3. On the project dashboard, locate the **Connection Details** box:
   - Select role `neondb_owner` and database `neondb`.
   - Copy the connection string starting with `postgresql://`.
4. Convert the URL to `postgresql+psycopg://` with `sslmode=require`:
   - On Linux/macOS:
     ```bash
     ./scripts/deploy/neon-url.sh "postgresql://alex:secret@ep-xyz.neon.tech/neondb?sslmode=require"
     ```
   - On Windows PowerShell:
     ```powershell
     .\scripts\deploy\neon-url.ps1 -Url "postgresql://alex:secret@ep-xyz.neon.tech/neondb?sslmode=require"
     ```
   Save the resulting string (starts with `postgresql+psycopg://...`). You will need it in Step 2.

---

## Step 2: Deploy Backend to Render (via Blueprint)

1. Push your repository (including `render.yaml`) to GitHub/GitLab.
2. Sign in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect your Git repository. Render will automatically detect `render.yaml` at the root and parse the `sparehub-api` service.
5. In the Blueprint creation screen, you will be prompted to provide values for variables marked `sync: false`:
   - **`DATABASE_URL`**: Paste your converted Neon URL from Step 1 (`postgresql+psycopg://...`).
   - **`CORS_ORIGINS`**: Enter a placeholder HTTPS domain for now, e.g., `https://sparehub.vercel.app` (you will update this in Step 4 once Vercel gives you your exact URL).
6. Click **Apply**.
   - Render builds the Docker container (`./backend/Dockerfile`).
   - On container start, it runs Alembic migrations (`alembic upgrade head`) and launches Uvicorn on port 8000.
7. Once deployment finishes, copy your Render web service URL from the dashboard:
   - Example: `https://sparehub-api-xxxx.onrender.com`

---

## Step 3: Deploy Frontend to Vercel

1. Open `frontend/vercel.json` in your editor.
2. Replace `https://YOUR-BACKEND.onrender.com` with your actual Render service URL from Step 2:
   ```json
   {
     "$schema": "https://openapi.vercel.sh/vercel.json",
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://sparehub-api-xxxx.onrender.com/api/:path*"
       },
       {
         "source": "/uploads/:path*",
         "destination": "https://sparehub-api-xxxx.onrender.com/uploads/:path*"
       },
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```
3. Commit and push `frontend/vercel.json` to your Git repository:
   ```bash
   git add frontend/vercel.json
   git commit -m "chore: configure Render backend URL in vercel.json"
   git push origin master
   ```
4. Sign in to [Vercel](https://vercel.com) and click **Add New...** > **Project**.
5. Import your Git repository and configure the project settings:
   - **Framework Preset:** Vite
   - **Root Directory:** Click "Edit" and select `frontend`
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `dist` (default)
   - **Environment Variables:**
     - `VITE_API_BASE_URL` = `/api`
6. Click **Deploy**.
7. Once deployed, Vercel will assign you a live production domain:
   - Example: `https://sparehub-alpha.vercel.app`

---

## Step 4: Synchronize CORS on Render

Now that you have your live Vercel URL:
1. Go to your Render Dashboard > **sparehub-api** service > **Environment**.
2. Find `CORS_ORIGINS`.
3. Update it to your exact Vercel frontend URL:
   - Value: `https://sparehub-alpha.vercel.app` (no trailing slash, must start with `https://`).
4. Click **Save Changes**. Render will automatically trigger a zero-downtime redeploy with the updated CORS policy.

---

## Step 5: Create Initial Store Administrator

Because production migrations create clean database tables without seeding default passwords, create your first Store Administrator account using the helper script:

- **On Linux / macOS:**
  ```bash
  ./scripts/deploy/create-admin-remote.sh
  ```
- **On Windows PowerShell:**
  ```powershell
  .\scripts\deploy\create-admin-remote.ps1
  ```

The script will:
1. Prompt for your Neon `DATABASE_URL` (masked, never printed).
2. Ask for Admin details (Employee ID, Full Name, Email, and Location Code, e.g., `ADM001`, `Admin User`, `admin@example.com`, `BLR`).
3. Ensure the initial location record exists in Neon.
4. Securely prompt for the admin password (min 12 characters).
5. Hash the password with Argon2id and create the administrator user in the database.

> [!TIP]
> You can create a local `.env.deploy.local` file (already gitignored) in the repo root containing `DATABASE_URL=postgresql+psycopg://...` so you don't have to re-enter it each time.

---

## Step 6: Verify Deployment with Smoke Test

Run the automated smoke test against your live frontend:

- **On Linux / macOS:**
  ```bash
  ./scripts/deploy/smoke-test.sh https://sparehub-alpha.vercel.app
  ```
- **On Windows PowerShell:**
  ```powershell
  .\scripts\deploy\smoke-test.ps1 -Url "https://sparehub-alpha.vercel.app"
  ```

The smoke test will:
1. Verify the frontend HTML index responds with HTTP 200.
2. Poll `/api/health` through Vercel's proxy rewrite (waiting up to 90 seconds if Render's container is waking from a cold start).
3. Validate `/api/health/db` to verify that Render is talking to Neon.
4. Output a summary table showing `[PASS]` or `[FAIL]` per check.

---

## Troubleshooting

### 1. Cold Starts & Initial Request Latency
- **Symptom:** First request after 15+ minutes takes 45–70 seconds or returns HTTP 502 / 504 temporarily.
- **Cause:** Render free web services spin down to 0 instances after ~15 minutes of inactivity. When a new HTTP request hits the service, Render spins up the container.
- **Solution:** Allow 60–90 seconds on first request. The `smoke-test` script automatically handles cold-start retries up to 90 seconds. To avoid cold starts in production, consider upgrading the Render service to the "Starter" plan ($7/mo) which remains always-on.

### 2. CORS Errors in Browser Console
- **Symptom:** `Access to fetch at '...' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present`.
- **Cause:**
  - `CORS_ORIGINS` in Render environment does not exactly match the browser's origin.
  - A trailing slash was included (e.g., `https://sparehub.vercel.app/` instead of `https://sparehub.vercel.app`).
  - Wildcards (`*`) or non-HTTPS URLs were supplied.
- **Solution:** In Render Dashboard > Environment, verify `CORS_ORIGINS` is exactly `https://<your-vercel-domain>.vercel.app` without a trailing slash.

### 3. "Invalid Host" HTTP 400 Errors
- **Symptom:** Requests return HTTP 400 with `Invalid host header`.
- **Cause:** `ALLOWED_HOSTS` was set in Render environment variables. Starlette's `TrustedHostMiddleware` blocks requests because Vercel reverse proxy and Render internal routing forward requests under different host headers.
- **Solution:** Leave `ALLOWED_HOSTS` completely unset / empty on Render. `backend/app/core/config.py` allows leaving `ALLOWED_HOSTS` unset, which safely disables host filtering when behind trusted proxies.

### 4. SECRET_KEY Validation Failure on Startup
- **Symptom:** Render container logs show:
  `[CRITICAL CONFIGURATION ERROR] Application failed to start due to invalid or missing configuration.`
  `CRITICAL SECURITY CONFIGURATION ERROR: In production environment (APP_ENV=production), SECRET_KEY must be a cryptographically secure random string of at least 32 characters, and cannot be a default/placeholder value.`
- **Cause:** `SECRET_KEY` in Render is less than 32 characters, missing, or contains words like `placeholder`, `changeme`, or `secret`.
- **Solution:** Ensure `SECRET_KEY` uses `generateValue: true` in `render.yaml`, or generate a 48+ character key using `./scripts/deploy/gen-secret.sh` (or `.\scripts\deploy\gen-secret.ps1`) and paste it into Render Environment settings.

### 5. PostgreSQL Database SSL Connection Errors
- **Symptom:** Backend logs show:
  `connection failed: server does not support SSL, but SSL was required` or `psycopg.OperationalError: no pg_hba.conf entry for host ..., SSL off`.
- **Cause:** Neon strictly requires encrypted TLS connections. The connection string must include `sslmode=require`, and the URL scheme must be `postgresql+psycopg://` (not `postgresql://`).
- **Solution:** Pass your Neon URL through `./scripts/deploy/neon-url.sh` (or `.\scripts\deploy\neon-url.ps1`) and update `DATABASE_URL` in the Render dashboard.

---

## Known Free-Tier Limitations

| Service / Resource | Free Tier Limitation | Operational Impact | Recommended Mitigation |
|:---|:---|:---|:---|
| **Render Web Service** | Spins down after 15 minutes of idle time | Cold start delays (30–60 seconds) on the first request after being idle. | Upgrade Render plan to Starter ($7/mo) for persistent uptime, or use an external health ping service (e.g. UptimeRobot) every 10 min. |
| **Render Storage** | Ephemeral container filesystem (`/app/uploads`) | Any catalog images uploaded via `/api/parts/...` are stored locally and will be deleted when Render restarts or redeploys. | Use S3-compatible cloud object storage (Cloudflare R2 free tier: 10GB free, 0 egress fees). |
| **Neon PostgreSQL** | Suspends compute after 5 minutes of idle time | 1–3 second delay on first query when resuming from suspend. | Automatic wake-up is transparent to FastAPI/SQLAlchemy connection pool. |
| **Neon PostgreSQL** | 0.5 GB storage cap on free tier | Exceeding 512MB storage will put project in read-only mode. | Ample for tens of thousands of inventory records and audit logs. Periodically prune old transaction logs if necessary. |
| **Vercel** | 100 GB bandwidth / month | Sufficient for high-traffic SPA delivery. | Free tier easily supports normal operational usage. |
