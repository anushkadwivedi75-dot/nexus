# NEXUS — PRODUCTION DEPLOYMENT GUIDE

**Version:** 1.3.1  
**Architecture Source of Truth:** `docs/NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1.md`

---

## 1. Architecture Overview

Nexus is deployed as a coordinated multi-container architecture orchestrated by Docker Compose:

```
                          Internet / Clients
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │   Nginx Gateway Proxy   │ (Port 80 / 443)
                     │ (combined_redacted log) │
                     └───────┬─────────┬───────┘
                             │         │
                /api & /ws   │         │  / (Static UI Assets)
                             ▼         ▼
        ┌─────────────────────────┐  ┌─────────────────────────┐
        │   FastAPI Web Service   │  │   Frontend Static Web   │
        │  (Uvicorn 2+ Workers)   │  │    (Nginx 1.27 Alpine)  │
        └───────┬─────────┬───────┘  └─────────────────────────┘
                │         │
                ▼         ▼
        ┌──────────────┐ ┌──────────────┐
        │  PostgreSQL  │ │    Redis     │
        │   16 Alpine  │ │   7 Alpine   │
        └──────────────┘ └──────────────┘
```

### Components
1. **Gateway Proxy (`gateway`)**:
   - Edge reverse proxy terminating HTTP/HTTPS.
   - Routes `/api/` to FastAPI backend and `/ws` with WebSocket upgrade protocol.
   - Enforces `combined_redacted` access logging (masking single-use WebSocket tickets).
   - Injects distributed `X-Request-ID` tracing header and security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`).
2. **FastAPI Backend (`backend`)**:
   - Multi-stage Python 3.12-slim image running non-root (`nexus` user, UID 10001).
   - Runs database migrations on boot (`alembic upgrade head`).
   - Connects using `nexus_migrator` for migrations and `nexus_app` for runtime queries.
3. **Frontend SPA (`frontend`)**:
   - Built with Vite and served via lean Nginx Alpine with SPA client-side routing fallback.
4. **PostgreSQL Database (`postgres`)**:
   - PostgreSQL 16 Alpine with initialized tri-role deployment architecture.
5. **Redis Cache & Pub/Sub (`redis`)**:
   - Redis 7 Alpine with password authentication and AOF persistence.

---

## 2. Prerequisites

- **Docker:** Engine version 24.0 or later
- **Docker Compose:** v2.20 or later
- **Ports:** Port `80` (HTTP) and optionally `443` (HTTPS) free on the host.

---

## 3. Quick Start (One-Command Deployment)

### Linux / macOS:
```bash
# 1. Clone repository and navigate to root
cd /path/to/nexus

# 2. Run deployment script
chmod +x deploy.sh
./deploy.sh
```

### Windows (PowerShell):
```powershell
cd C:\PROJECTS\nexus
.\deploy.ps1
```

### Manual Docker Compose Command:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Access the application:
- **Web UI:** [http://localhost](http://localhost)
- **API Documentation:** [http://localhost/api/v1/docs](http://localhost/api/v1/docs)
- **Health Check:** [http://localhost/api/v1/health](http://localhost/api/v1/health)

---

## 4. Environment Configuration

Copy `.env.production.example` to `.env.production` and configure the following variables:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `APP_ENV` | Application environment | `production` |
| `DEBUG` | Enable/disable debug mode | `False` |
| `PORT` | Public HTTP port | `80` |
| `JWT_SECRET` | HMAC-SHA256 secret for access tokens | Minimum 32 characters |
| `TOKEN_ENCRYPTION_KEY` | 256-bit AES-256-GCM hex key | Exactly 64 hex characters |
| `POSTGRES_DB` | PostgreSQL database name | `nexus_prod` |
| `POSTGRES_USER` | Migration database user | `nexus_migrator` |
| `POSTGRES_PASSWORD` | Migration user password | Strong random string |
| `REDIS_PASSWORD` | Redis authentication password | Strong random string |
| `CORS_ORIGINS` | Whitelisted frontend origins | `["https://nexus.yourdomain.com"]` |
| `WEB_CONCURRENCY` | Uvicorn worker count | `2` (or CPU count $\times 2$) |
| `RUN_MIGRATIONS` | Auto-apply Alembic migrations on boot | `true` |

---

## 5. Database Roles & Deployment Privilege Separation (ADR-07)

Nexus formalizes **Three Deployment Roles** per Section 13.2 of the technical blueprint:

1. **`nexus_migrator`**:
   - Used by Alembic during CI/CD deployment or container boot.
   - Holds full DDL (`CREATE`, `ALTER`, `DROP`) and DML privileges on the schema.
2. **`nexus_app`**:
   - Used by the FastAPI web service pods during runtime.
   - Holds `SELECT`, `INSERT`, `UPDATE`, `DELETE` privileges.
   - **Immutable Audit Trail:** `UPDATE`, `DELETE`, and `TRUNCATE` are strictly revoked on `audit_logs`.
3. **`nexus_maintenance`**:
   - Used by isolated retention cron workers (running at 03:00 UTC).
   - Holds `SELECT` and `DELETE` on `audit_logs` (for 365-day retention purge) and `outbox_events` (for 7-day retention purge).

---

## 6. Real-Time WebSocket & Log Redaction

The Gateway Nginx enforces Section 12.1 log redaction:
- WebSocket single-use handshake tickets passed in query strings (`?ticket=...`) are automatically masked in Nginx access logs:
  ```nginx
  map $request_uri $redacted_request_uri {
      ~^(?<path>[^?]+)\?(?:.*&)?ticket=[^&]*(?<rest>.*)$  $path?[REDACTED]$rest;
      default                                            $request_uri;
  }
  ```
- All requests log with correlation trace IDs (`$request_id`) forwarded downstream to the FastAPI backend as `X-Request-ID`.

---

## 7. Backups and Disaster Recovery

### Database Backup (Logical Snapshot):
```bash
docker exec -t nexus_postgres_prod pg_dump -U nexus_migrator -d nexus_prod -F c -b -v -f /tmp/nexus_backup.dump
docker cp nexus_postgres_prod:/tmp/nexus_backup.dump ./nexus_backup_$(date +%Y%m%d_%H%M%S).dump
```

### Database Restore:
```bash
docker cp ./nexus_backup.dump nexus_postgres_prod:/tmp/nexus_backup.dump
docker exec -t nexus_postgres_prod pg_restore -U nexus_migrator -d nexus_prod --clean --if-exists /tmp/nexus_backup.dump
```

---

## 8. Troubleshooting & Common Issues

### Issue 1: Port 80 or 8000 already in use
- **Symptoms:** `Bind for 0.0.0.0:80 failed: port is already allocated`
- **Solution:** 
  1. Identify conflicting process:
     - Linux/macOS: `sudo lsof -i :80` or `docker ps`
     - Windows: `Get-NetTCPConnection -LocalPort 80`
  2. If an old container is occupying the port: `docker stop <container_name>`
  3. Alternatively, specify an alternate port in `.env.production`: `PORT=8080`

### Issue 2: Viewing Container Logs
```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View backend logs specifically
docker compose -f docker-compose.prod.yml logs -f backend

# View gateway access logs
docker compose -f docker-compose.prod.yml logs -f gateway
```

### Issue 3: Re-running Database Migrations Manually
```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## 9. Production Readiness Checklist

- [x] Lean, multi-stage production Dockerfiles with non-root security context.
- [x] Docker Compose production topology with automatic container healthchecks.
- [x] Nginx reverse proxy with SSL termination readiness and WebSocket upgrade proxying.
- [x] Redacted log format masking sensitive tickets (`combined_redacted`).
- [x] Immutability on `audit_logs` enforced at database role level (`nexus_app`).
- [x] Database migrations auto-applied on container startup.
- [x] Cross-origin CORS whitelist strictly constrained.
- [x] Production cookie flags configured (`__Host-nexus_rt` with `Secure=True`).
- [x] One-command deployment scripts for Linux and Windows (`deploy.sh`, `deploy.ps1`).

