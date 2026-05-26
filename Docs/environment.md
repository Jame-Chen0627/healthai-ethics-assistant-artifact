# Environment Variables

## Backend (`backend/.env` locally, Render env panel in production)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./app.db` | SQLAlchemy DSN. PostgreSQL can be used in production. SQLite works for local dev and review. |
| `SECRET_KEY` | `change-me-in-production` | Signs JWT access tokens. Use a random value in production. **Rotating invalidates every existing token.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT lifetime in minutes (24 h default). |
| `GEMINI_API_KEY` | `""` | Google AI Studio key used by `services/llm_service.py`. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model identifier. Other valid values: `gemini-2.5-pro`, `gemini-2.0-flash`. |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | **JSON array** of allowed frontend origins. Must include the deployed frontend URL in production. |
| `BACKEND_URL` | `http://localhost:8000` | Public URL of this API. Used to build OAuth callbacks. |
| `FRONTEND_URL` | `http://localhost:5173` | Public URL of the SPA. Used for OAuth redirects after sign-in. |
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth client. |
| `GOOGLE_CLIENT_SECRET` | `""` | Google OAuth secret. |
| `GITHUB_CLIENT_ID` | `""` | GitHub OAuth client. |
| `GITHUB_CLIENT_SECRET` | `""` | GitHub OAuth secret. |

> Anything not listed above is ignored (see `model_config = SettingsConfigDict(extra="ignore")` in `backend/app/config.py`).

### `.env` formatting gotchas
- `CORS_ORIGINS` must be **valid JSON**, not a comma-separated string:
  ```env
  CORS_ORIGINS=["http://localhost:5173","https://your-frontend.example"]
  ```
- Numeric variables (`ACCESS_TOKEN_EXPIRE_MINUTES`) must not be quoted.
- Trailing whitespace in secrets breaks signature checks — strip carefully.

---

## Frontend (`frontend/.env` locally, Cloudflare Pages env panel in production)

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL the SPA hits via Axios. Set to the deployed backend URL in production. |

Vite only exposes vars that start with `VITE_`. Other variables in
`frontend/.env` are silently ignored on the client.

---

## OAuth provider configuration

| Provider | Authorized callback |
|----------|---------------------|
| Google | `${BACKEND_URL}/auth/google/callback` |
| GitHub | `${BACKEND_URL}/auth/github/callback` |

After changing `BACKEND_URL`, update the redirect URI list in the provider
console **and** restart the backend.
