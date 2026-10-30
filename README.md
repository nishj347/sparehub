# Spare Parts Management & Discovery System

Enterprise foundation and technical architecture skeleton for a Spare Parts Management & Discovery System designed for enterprise scale (e.g., ITC manufacturing plants and centralized stores).

---

## 1. Architecture Overview

The system is architected as an enterprise monolith:

```
[React 18 + TypeScript + Vite + Tailwind CSS]  (Port 5173)
                      │
                      ▼ HTTP REST API (JSON)
           [FastAPI + Python 3.11+]             (Port 8000)
                      │
                      ▼ SQLAlchemy 2.x ORM / Connection Pool
             [PostgreSQL 16 Engine]             (Port 5432)
```

- **Frontend**: Single-page application built with React 18, TypeScript (strict mode enabled), Vite, and Tailwind CSS.
- **Backend**: High-performance REST API built with FastAPI, SQLAlchemy 2.x, Alembic, and `psycopg` (v3 binary).
- **Database**: PostgreSQL 16 containerized via Docker Compose with dedicated persistent volume and container health checks.
- **Security & Integrity**: Strict CORS whitelist via environment configuration, global structured error handling, and zero hardcoded secrets.

---

## 2. Repository Structure

```
sparehub/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── health.py        # Health and DB probe endpoints
│   │   │   ├── __init__.py
│   │   │   └── router.py            # Central router aggregating all routes under /api
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Typed settings via pydantic-settings
│   │   │   └── logging.py           # Structured application logging setup
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   │   └── session.py           # Engine, SessionLocal, get_db dependency
│   │   ├── models/
│   │   │   └── __init__.py          # Target for ORM models (Module 2)
│   │   ├── schemas/
│   │   │   └── __init__.py          # Target for Pydantic schemas
│   │   ├── services/
│   │   │   └── __init__.py          # Target for domain business logic
│   │   ├── __init__.py
│   │   └── main.py                  # FastAPI initialization & global middleware
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── .gitkeep             # Version migrations target directory
│   │   ├── env.py                   # Migration environment configured with app settings
│   │   ├── README
│   │   └── script.py.mako           # Migration template
│   ├── alembic.ini                  # Alembic CLI configuration
│   ├── requirements.txt             # Pinned minimal Python dependencies
│   └── .env.example                 # Backend environment variable template
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts            # Typed fetch client using VITE_API_BASE_URL
│   │   ├── components/layout/
│   │   │   ├── AppShell.tsx         # Responsive enterprise layout
│   │   │   ├── Sidebar.tsx          # Collapsible navigation drawer
│   │   │   └── Topbar.tsx           # Context header & user profile area
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx    # System status verification dashboard
│   │   │   ├── PlaceholderPage.tsx  # Extensible stub for future modules
│   │   │   └── NotFoundPage.tsx     # 404 handler
│   │   ├── routes/
│   │   │   └── index.tsx            # Route configuration
│   │   ├── types/
│   │   │   └── index.ts             # Shared frontend TypeScript interfaces
│   │   ├── App.tsx                  # App entry root
│   │   ├── index.css                # Tailwind directives & core typography
│   │   └── main.tsx                 # DOM bootstrap
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   └── .env.example                 # Frontend environment variable template
├── docker-compose.yml               # PostgreSQL 16 container definition
├── .gitignore
└── README.md
```

---

## 3. Prerequisites

Ensure the following tools are installed on your workstation:

- **Docker Desktop** (or Docker Engine + Compose v2+)
- **Python 3.11+**
- **Node.js 18+** & **npm**

---

## 4. Environment Configuration

Copy the example environment files into local active `.env` files for both backend and frontend.

### 4.1 Backend Environment

```bash
# From workspace root
copy backend\.env.example backend\.env       # Windows PowerShell / CMD
# or: cp backend/.env.example backend/.env    # Linux / macOS
```

Key backend variables in `backend/.env`:
- `DATABASE_URL`: Connection string (`postgresql+psycopg://postgres:postgres@localhost:5432/sparehub_dev`)
- `APP_ENV`: `development` or `production`
- `CORS_ORIGINS`: Comma-separated list of allowed origins (default `http://localhost:5173,http://127.0.0.1:5173`)
- `SECRET_KEY`: Cryptographic signing key (minimum 32 characters; used in Module 3)
- `UPLOAD_DIR`: Target path for media and documents (used in later modules)

### 4.2 Frontend Environment

```bash
# From workspace root
copy frontend\.env.example frontend\.env     # Windows PowerShell / CMD
# or: cp frontend/.env.example frontend/.env  # Linux / macOS
```

Key frontend variable in `frontend/.env`:
- `VITE_API_BASE_URL`: Base URL for API calls (default `http://localhost:8000/api`)

---

## 5. Starting the PostgreSQL Database

Run Docker Compose to start the isolated PostgreSQL container:

```bash
docker compose up -d
```

To verify the container is running and healthy:

```bash
docker compose ps
```

The database container uses:
- **Port**: `5432` exposed locally
- **Database Name**: `sparehub_dev`
- **User**: `postgres`
- **Password**: `postgres`
- **Data Volume**: `postgres_data` (persisted on disk)

---

## 6. Backend Setup & Execution

### 6.1 Create and Activate Virtual Environment

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate on Windows:
.\venv\Scripts\activate
# Activate on Linux / macOS:
# source venv/bin/activate
```

### 6.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 6.3 Run Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`.

- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Interactive ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 6.4 Verify Alembic Migrations Configuration

With the virtual environment active and PostgreSQL running, verify Alembic can connect and inspect database revision state:

```bash
alembic current
```

*(Outputs no errors; no revisions exist yet as database models will be introduced in Module 2.)*

---

## 7. Frontend Setup & Execution

Open a separate terminal window:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173).

### 7.1 Verify TypeScript & Production Build

To confirm type-safety with strict checks:

```bash
# TypeScript verification
npx tsc --noEmit

# Production build verification
npm run build
```

---

## 8. Verifying End-to-End System Health

### 8.1 Via Browser UI

1. Open [http://localhost:5173](http://localhost:5173).
2. The **System Status** card on the dashboard will probe both the API and database on load.
3. When both services are up:
   - **FastAPI REST Backend**: Displays `Online` (green indicator, status `ok`, environment `development`).
   - **PostgreSQL Database**: Displays `Connected` (green indicator, query `SELECT 1` succeeded).
4. If PostgreSQL is stopped (`docker compose stop postgres`), the UI clearly flags the database as `Unreachable` with HTTP 503 error details and presents a **Retry Connection** button.
5. If the FastAPI backend is stopped, the UI cleanly handles network failure, flags the backend as `Offline`, and prevents frontend application crashes.

### 8.2 Via Terminal / Curl

```bash
# Test API Health
curl -s http://localhost:8000/api/health
# Response: {"status":"ok","environment":"development"}

# Test Database Health
curl -s http://localhost:8000/api/health/db
# Response: {"status":"ok","database":"connected"}
```

---

## 9. Error Handling & Security Conventions

- **Structured JSON Errors**: Every API exception returns `{"detail": "...", "code": "..."}`.
- **Fail-Fast Startup**: If `DATABASE_URL` is omitted or empty, backend startup halts immediately with a clear error message.
- **Production Information Masking**: Internal server exception tracebacks are withheld when `APP_ENV=production`.
- **CORS Whitelisting**: The API rejects unconfigured origins; wildcards (`*`) are disallowed by validator.
- **No Secrets in Version Control**: `.env` files are gitignored; templates are kept in `.env.example`.
