# Nexus — Real-Time Team Collaboration & Project Management SaaS

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

Nexus is a production-minded, multi-tenant team collaboration and project management SaaS platform inspired by Linear, Notion, and ClickUp.

---

## 1. Prerequisites

Ensure the following tools are installed on your host machine:

- **Docker & Docker Compose:** Docker Desktop 4.x+ with Compose v2.x+
- **Python:** Python 3.12+ (or managed via [`uv`](https://docs.astral.sh/uv/))
- **Node.js:** Node.js 20+ (with npm 10+)
- **Git**

---

## 2. Repository Structure

```
c:\PROJECTS\nexus\
├── .env.example              # Root environment template
├── .gitignore                # Root git ignore specification
├── docker-compose.yml        # Infrastructure topology (PostgreSQL 16 & Redis 7)
├── README.md                 # Project documentation and developer handbook
├── docs/                     # Architectural specifications
│   └── NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1.md
├── backend/                  # FastAPI & SQLAlchemy 2.x Async Backend
│   ├── alembic.ini           # Alembic migration configuration
│   ├── pyproject.toml        # Backend build configuration & dependencies
│   ├── requirements.txt      # Pinned dependency requirements
│   ├── test_health.py        # Health probe test script
│   ├── test_live_server.py   # Live server socket verification script
│   ├── alembic/              # Database migration versions & runner
│   │   ├── env.py            # Async migration runner connected to Base.metadata
│   │   ├── script.py.mako    # Migration template
│   │   └── versions/         # Migration versions (77c880605cf5_initial_schema_v1_3_1.py)
│   └── app/
│       ├── main.py           # FastAPI application entry point & CORS
│       ├── api/              # API router hierarchy
│       │   └── v1/
│       │       ├── api.py    # v1 Router aggregation
│       │       └── endpoints/
│       │           └── health.py # GET /api/v1/health
│       ├── core/             # Configuration & database session factories
│       │   ├── config.py     # Pydantic BaseSettings
│       │   └── database.py   # Reusable async engine & AsyncSessionLocal
│       ├── models/           # Complete 17 SQLAlchemy ORM models
│       │   ├── base.py       # DeclarativeBase
│       │   ├── user.py
│       │   ├── refresh_token.py
│       │   ├── workspace.py
│       │   ├── workspace_member.py
│       │   ├── workspace_invitation.py
│       │   ├── project.py
│       │   ├── project_member.py
│       │   ├── task_status.py
│       │   ├── task.py
│       │   ├── task_assignee.py
│       │   ├── tag.py
│       │   ├── task_tag.py
│       │   ├── comment.py
│       │   ├── notification.py
│       │   ├── activity_log.py
│       │   ├── audit_log.py
│       │   └── outbox_event.py
│       └── schemas/          # Pydantic validation schemas
│           └── health.py
└── frontend/                 # React 19 + TypeScript + Vite UI
    ├── package.json
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx           # Application route definitions
        ├── components/
        │   ├── layout/       # Shell, Sidebar, Header, CommandPalette
        │   └── ui/           # Radix UI primitives & styled components
        ├── pages/            # Overview, Projects, Tasks, Settings, etc.
        └── stores/           # Zustand state management
```

---

## 3. Environment Setup & Configuration

1. Copy the example configuration to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Review the core parameters in `.env`:
   - `POSTGRES_DB`: Name of the development database (`nexus_dev`)
   - `POSTGRES_USER`: Database administrator/migrator role (`nexus_migrator`)
   - `POSTGRES_PASSWORD`: Migrator credentials (`migrator_dev_password`)
   - `REDIS_PASSWORD`: Redis authentication token (`dev_redis_password`)
   - `DATABASE_URL`: Async SQLAlchemy database URL (`postgresql+asyncpg://...`)

---

## 4. Production Deployment

To deploy the entire production stack (Nginx Gateway, Frontend SPA, Backend API, PostgreSQL 16, Redis 7):

### One-Command Deployment:
- **Linux / macOS:**
  ```bash
  chmod +x deploy.sh
  ./deploy.sh
  ```
- **Windows PowerShell:**
  ```powershell
  .\deploy.ps1
  ```
- **Manual Docker Compose:**
  ```bash
  docker compose -f docker-compose.prod.yml up -d --build
  ```

The complete production system will be operational at:
- **Application Web UI:** `http://localhost`
- **Backend API & Swagger Docs:** `http://localhost/api/v1/docs`
- **Gateway Health Check:** `http://localhost/healthz`

For full production architecture, SSL configuration, database role separation, and backup policies, refer to [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## 5. Development Setup & Startup

1. Create and activate a Python 3.12+ virtual environment:
   ```bash
   cd backend
   python -m venv .venv

   # Windows PowerShell
   .venv\Scripts\Activate.ps1

   # macOS / Linux
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run database migrations to provision the schema:
   ```bash
   alembic upgrade head
   ```

4. Start the FastAPI development server with hot-reload:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 6. Frontend Setup & Startup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The application interface will be live at `http://localhost:5173`.

---

## 7. Database Migrations (Alembic)

All migrations run against PostgreSQL 16 using SQLAlchemy 2.x async engine:

```bash
cd backend

# Apply all migrations to the latest revision
alembic upgrade head

# Roll back the most recent migration step
alembic downgrade -1

# Roll back completely to a blank database
alembic downgrade base

# Generate a new autodetected migration revision
alembic revision --autogenerate -m "describe_migration"
```

---

## 8. Health Endpoint Verification

To verify that the API server is operational without authentication:

```bash
# Using curl:
curl -i http://localhost:8000/api/v1/health

# Expected HTTP Response:
# HTTP/1.1 200 OK
# content-type: application/json
#
# {
#   "status": "ok",
#   "service": "nexus-api",
#   "version": "0.1.0",
#   "environment": "development"
# }
```

You can also run the automated test suite script:
```bash
python test_health.py
python test_live_server.py
```

---

## 9. Common Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `failed to connect to docker API` | Docker Desktop is stopped | Open Docker Desktop and ensure the engine status icon is green. |
| `HTTP 502 Bad Gateway on Sign In` | Backend server not running or port 8000 conflicting | Ensure backend is running (`uvicorn app.main:app`) and no other container (`docker ps`) occupies port 8000. |
| `npm error enoent package.json` | Running `npm` inside `backend/` | Navigate to `frontend/` (`cd frontend`) before running npm commands. |
| `Port 5432 already in use` | Local PostgreSQL instance conflicting | Stop local PostgreSQL service (`net stop postgresql-x64-16`) or change `POSTGRES_PORT` in `.env`. |
| `Port 6379 already in use` | Local Redis service conflicting | Change `REDIS_PORT` in `.env` or stop the local Redis service. |
| `alembic: connection refused` | Database container not healthy | Run `docker-compose ps` and wait until `nexus_postgres` reports `(healthy)`. |
| `module 'app' not found` | `PYTHONPATH` not pointing to `backend` | Execute commands from within `backend/` or set `PYTHONPATH=.`. |

