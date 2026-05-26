from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from .config import settings
from .database import Base, engine
from .routers import auth, chat, ethics

# Create DB tables on startup (for development; use Alembic for production)
Base.metadata.create_all(bind=engine)


def _ensure_chat_session_columns() -> None:
    """Lightweight forward-only migration: add new columns to chat_sessions
    if they don't already exist. Safe for sqlite and postgres."""
    try:
        inspector = inspect(engine)
        if "chat_sessions" not in inspector.get_table_names():
            return
        existing = {col["name"] for col in inspector.get_columns("chat_sessions")}
        statements = []
        if "topic" not in existing:
            statements.append("ALTER TABLE chat_sessions ADD COLUMN topic VARCHAR(120)")
        if "topic_prompt" not in existing:
            statements.append("ALTER TABLE chat_sessions ADD COLUMN topic_prompt TEXT")
        if "system_context" not in existing:
            statements.append("ALTER TABLE chat_sessions ADD COLUMN system_context TEXT")
        if "custom_persona" not in existing:
            statements.append("ALTER TABLE chat_sessions ADD COLUMN custom_persona TEXT")
        if "custom_persona_name" not in existing:
            statements.append("ALTER TABLE chat_sessions ADD COLUMN custom_persona_name VARCHAR(120)")
        if statements:
            with engine.begin() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))
    except Exception:  # pragma: no cover - never block app startup on migration
        pass


_ensure_chat_session_columns()

app = FastAPI(
    title="HealthAI Ethics Assistant",
    description="HealthAI Ethics Assistant — a scalable RAG-based dialogue system for healthcare AI ethics requirements engineering, grounded in EU AI Act / NIST AI RMF. Additional topics are available as extensions.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ethics.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {
        "name": "HealthAI Ethics Assistant API",
        "version": "2.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db():
    """Verify the database connection is reachable. Returns 200 on success,
    503 with the error message on failure."""
    from sqlalchemy import text
    from fastapi import HTTPException
    from .database import engine, _database_url

    backend = _database_url.split("://", 1)[0]
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "backend": backend}
    except Exception as exc:  # pragma: no cover - surfaces real infra errors
        raise HTTPException(status_code=503, detail=f"db unreachable: {exc}")
