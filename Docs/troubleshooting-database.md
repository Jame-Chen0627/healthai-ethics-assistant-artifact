# Database Troubleshooting

The app uses **SQLAlchemy 2.x** with the engine defined in
`backend/app/database.py`. In production it points at PostgreSQL; for
local dev and tests it falls back to SQLite.

---

## 1. Is the database reachable?

The fastest check is the dedicated endpoint added to the API:

```bash
BASE=https://your-backend.example   # or http://localhost:8000
curl -i $BASE/health/db
```

| HTTP | Meaning |
|------|---------|
| `200 {"status":"ok","backend":"postgresql"}` | Engine connected and ran `SELECT 1` |
| `200 {"status":"ok","backend":"sqlite"}` | Local SQLite mode |
| `503 {"detail":"db unreachable: ..."}` | Connection failed — read the error |

The endpoint code lives at the bottom of [`backend/app/main.py`](../backend/app/main.py).

---

## 2. Inspect the DSN your app actually uses

```bash
cd backend && source venv/bin/activate
python -c "from app.database import _database_url; print(_database_url)"
```

Notes:
- Some providers expose Postgres URLs starting with `postgres://`. The app rewrites
  them to `postgresql://` automatically (see top of `database.py`).
- Some managed Postgres providers require SSL. The default driver handles it, but if
  you ever switch to a custom driver string add `?sslmode=require`.

---

## 3. Run a one-off query

```bash
cd backend && source venv/bin/activate

python - <<'PY'
from app.database import engine
from sqlalchemy import text
with engine.connect() as c:
    print(c.execute(text("SELECT 1")).scalar())
PY
```

A printed `1` means the network path, credentials, and SSL all work. Any
exception will name the exact failure (`could not connect to server`,
`password authentication failed`, `SSL connection has been closed
unexpectedly`, etc.).

---

## 4. Check tables and row counts

```bash
python - <<'PY'
from sqlalchemy import inspect
from app.database import engine, SessionLocal
from app import models

print("tables:", inspect(engine).get_table_names())
with SessionLocal() as s:
    for cls in (models.User, models.ChatSession, models.ChatMessage):
        print(f"{cls.__tablename__}: {s.query(cls).count()}")
PY
```

Expected tables (created automatically on startup): `users`, `chat_sessions`,
`chat_messages`. If a table is missing, the FastAPI process probably never
booted successfully — check backend logs.

---

## 5. Connect with a native client

### PostgreSQL (Render)
```bash
# Use the External Database URL from the Render dashboard
psql "$DATABASE_URL" -c "select now();"
psql "$DATABASE_URL" -c "\dt"
psql "$DATABASE_URL" -c "select id, username, email, created_at from users order by id desc limit 10;"
```

### SQLite (local)
```bash
sqlite3 backend/app.db ".tables"
sqlite3 backend/app.db "select id, username, email from users;"
```

---

## 6. Common failures

| Error from `/health/db` or `psql` | Cause | Fix |
|----|----|----|
| `could not translate host name` | Wrong hostname / DNS | Re-copy DSN from Render → Connect → External Database URL |
| `password authentication failed` | Old credentials | Rotate password in Render and update env var |
| `SSL connection has been closed unexpectedly` | Network blip / cold start | Retry; if persistent, prefer the **Internal** DB URL when both services are in the same Render region |
| `database "..." does not exist` | DSN points at wrong DB | Use the URL Render generated for this service, not a hand-written one |
| `relation "users" does not exist` | Tables never created | App startup failed before `create_all` ran — check backend logs |
| `OperationalError: too many connections` | Connection pool leak / many cold starts | Restart the service; consider `pool_pre_ping=True` if it recurs |

---

## 7. Resetting / migrating

There is **no Alembic migration suite** yet — schemas are auto-created from
`models.py` on startup. To apply model changes safely:

```bash
# Local SQLite — destructive
rm backend/app.db
uvicorn app.main:app --reload   # recreates with new schema
```

For Render Postgres, prefer adding columns via `psql` directly until Alembic
is introduced:

```sql
ALTER TABLE users ADD COLUMN avatar_url TEXT;
```

> ⚠️ Never run `DROP TABLE` on the production DB without an export.

Backup & restore (Render Postgres):
```bash
pg_dump "$DATABASE_URL" -Fc -f backup.dump
pg_restore -d "$DATABASE_URL" backup.dump
```

---

## 8. Render Postgres lifecycle reminders

- **Free Postgres expires after 90 days.** Render emails before expiry; export
  the data with `pg_dump` and recreate before the deadline, or upgrade to a
  paid tier.
- The instance is **paused after long idle periods** on free; first call may
  take 30–60s to wake. Hitting `/health/db` once is enough to warm it.
- The dashboard shows current connection count, CPU, and disk. Spikes in
  connections usually mean cold-start churn from Cloudflare workers /
  uptime monitors.
