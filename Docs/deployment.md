# Deployment

The project can be deployed with any Python web host, managed PostgreSQL
database, and static frontend host. The development version used this general
shape:

| Layer | Host | URL |
|-------|------|-----|
| Backend (FastAPI) | Python web service | `https://your-backend.example` |
| Database (PostgreSQL) | Render Managed Postgres | linked via `DATABASE_URL` |
| Frontend (Vue) | Static site host | `https://your-frontend.example` |
| Access gateway | Optional access control | reviewer/institution allow-list |

For anonymous review, deployment automation is optional. Do not publish provider
tokens or production secrets in the artifact repository.

---

## Backend Deployment

Configuration lives in [`render.yaml`](../render.yaml) at the repo root.

```yaml
services:
  - type: web
    name: healthai-ethics-api
    rootDir: backend
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

### Required env vars
Set these in your deployment provider's environment variable panel:

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | PostgreSQL URL or local SQLite URL |
| `SECRET_KEY` | Random JWT signing secret; rotating invalidates JWTs |
| `GEMINI_API_KEY` | From [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | e.g. `gemini-2.5-flash` |
| `BACKEND_URL` | Public backend URL |
| `FRONTEND_URL` | Public frontend URL |
| `CORS_ORIGINS` | JSON array of allowed origins |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | OAuth |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime |

Full reference: [environment.md](environment.md).

### Manual redeploy
Use your provider's redeploy command or dashboard action after changing
environment variables.

### Health checks
- `GET /health` → liveness (used by Render `healthCheckPath`).
- `GET /health/db` → DB connectivity (do **not** point Render's health check
  at this — DB hiccups would restart the app).

---

## Frontend Deployment

Project settings:

| Field | Value |
|-------|-------|
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `frontend` |
| Node version | 20.x |
| Production branch | `main` |

### Environment variables
| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://your-backend.example` |

Set the same value for both production and preview unless you maintain a
separate staging API.

---

## Local end-to-end run

```bash
# Terminal 1 — backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev   # http://localhost:5173 with VITE_API_BASE_URL=http://localhost:8000
```

The frontend already defaults to `http://localhost:8000` when
`VITE_API_BASE_URL` is unset.

---

## Release checklist

1. `cd backend && source venv/bin/activate && python -m pytest -q` (5 tests).
2. `cd frontend && npm run build` (must succeed; Cloudflare uses the same).
3. `git add -A && git commit -m "..." && git push origin main`.
4. Watch the backend and frontend deployment logs go green.
5. Smoke test:
   ```bash
   curl https://your-backend.example/health/db
   ```
6. Open the Pages URL, log in, send one ethics chat message.
