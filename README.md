# HealthAI Ethics Assistant Artifact

> Anonymous replication package for double-blind review.

**HealthAI Ethics Assistant** helps users create, validate, compare, curate and
export requirements for healthcare AI ethics. The current application domain is
**HealthAI Ethics**, grounded in a curated knowledge base of EU AI Act articles,
NIST AI RMF controls and practitioner findings across privacy, safety, bias,
transparency and accountability.

The application now supports mixed user personas, per-chat context, clickable
regulation references, per-chat requirement preferences, and Word document
export for accepted requirements. Adaptive topics are kept as a future extension
rather than exposed in the current HealthAI-focused UI.

Reviewer-facing artifact materials are provided in:

- `knowledge_base/`: EU AI Act, NIST AI RMF and practitioner findings in JSON.
- `prompts/`: Create, Validate and Compare prompt templates.
- `Docs/artifact_description.md`: package overview and workflow traceability.
- `Docs/anonymisation.md`: what has been removed or excluded for review.
- `evaluation/`: anonymised TAM/SUS materials and aggregate calculations.

| Layer | Stack |
|-------|-------|
| Backend | FastAPI · SQLAlchemy 2 · Pydantic v2 · Python 3.11 |
| Frontend | Vue 3 (`<script setup>`) · Vite 8 · Vue Router |
| LLM | Google Gemini (`gemini-2.5-flash` by default) |
| Storage | PostgreSQL in production, SQLite for local/tests |
| Auth | Username/password JWT · Google OAuth · GitHub OAuth · guest mode |
| Deploy | Render API + Postgres · Cloudflare Pages SPA |

---

## Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                    Vue 3 Frontend                        │
│ EthicsAssistantView · ChatSidebar · NewChatModal         │
│ DevPanel · Create/Validate/Compare cards · DOCX preview  │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTPS (Axios + JWT)
┌──────────────────────────▼───────────────────────────────┐
│                    FastAPI Backend                       │
│ /auth · /ethics · /chat · /health · /health/db           │
│ services/ethics_service.py ──► Gemini API                │
│ services/docx_service.py    ──► DOCX export              │
│ data/kb.py loads frameworks + practitioner findings      │
└──────────────────────────┬───────────────────────────────┘
                           │
                ┌──────────▼──────────┐
                │ PostgreSQL / SQLite │
                │ users               │
                │ chat_sessions       │
                │ chat_messages       │
                │ chat_requirement_preferences │
                └─────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11
- Node.js 20+
- A Google Gemini API key from <https://aistudio.google.com/apikey>

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

# Then edit .env as needed. A minimal local configuration is:
DATABASE_URL=sqlite:///./app.db
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=change_me
CORS_ORIGINS=["http://localhost:5173"]
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

uvicorn app.main:app --reload --port 8000
```

API docs are available at <http://localhost:8000/docs>. Tables are created on
startup for development. Lightweight forward migrations are included for
session context columns; production should still prefer proper Alembic
migrations for long-term maintenance.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at <http://localhost:5173>. If `VITE_API_BASE_URL` is unset,
it defaults to `http://localhost:8000`.

### Tests And Checks

```bash
cd backend && source venv/bin/activate
python -m pytest -q

cd ../frontend
npm run build
```

---

## Repository Layout

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, health endpoints
│   │   ├── config.py            # pydantic-settings
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── models.py            # User, sessions, messages, requirement preferences
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── data/
│   │   │   ├── kb.py
│   │   │   ├── frameworks.json
│   │   │   └── triangulation_findings.json
│   │   ├── routers/
│   │   │   ├── auth.py          # /auth
│   │   │   ├── ethics.py        # /ethics create/validate/compare/chat
│   │   │   └── chat.py          # /chat sessions, preferences, DOCX export
│   │   └── services/
│   │       ├── ethics_service.py
│   │       ├── llm_service.py
│   │       └── docx_service.py
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   └── runtime.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/index.js
│   │   ├── router/index.js
│   │   ├── views/
│   │   │   ├── EthicsAssistantView.vue
│   │   │   ├── LoginView.vue
│   │   │   └── OAuthCallback.vue
│   │   ├── utils/guestSessions.js
│   │   └── components/
│   │       ├── ChatSidebar.vue · ChatMessage.vue
│   │       ├── NewChatModal.vue · DevPanel.vue
│   │       ├── GuidelineRefBadge.vue
│   │       └── cards/{Create,Validate,Compare}Card.vue
│   └── vite.config.js
│
├── Docs/
│   ├── artifact_description.md
│   ├── setup.md
│   └── anonymisation.md
├── evaluation/
├── knowledge_base/
├── prompts/
├── render.yaml
└── README.md
```

---

## Main Features

### Topic-Aware Chat Sessions

Each chat has its own session-level context:

- selected topic and optional topic prompt
- selected persona or inferred mixed persona
- optional project/system context
- saved conversation messages
- accepted/rejected/suppressed requirement preferences

Logged-in sessions are stored in the backend database. Guest sessions are kept
in browser `sessionStorage` for the current tab.

### Persona Selection

Users can choose a fixed persona:

- Healthcare Professional
- Software Engineer
- Healthcare Researcher

Or choose **Let System Decide**, which runs a 20-question questionnaire. The
frontend computes a mixed persona from weighted HCP/SEng/HCR scores and passes a
compact JSON persona description to the backend as prompt context. Mixed
personas are displayed with a generic user icon in the chat list.

### Create / Validate / Compare

- **Create** generates ethical concerns and implementable requirements.
- **Validate** checks an existing requirement against topic-specific guidance or
  the built-in HealthAI knowledge base.
- **Compare** compares a draft requirement with practitioner findings or
  practical topic-specific concerns, then proposes an enhanced requirement.

The backend auto-classifies free-form prompts into one of these modes through
`/ethics/chat`.

### Clickable Regulation References

Guideline reference pills such as `EU AI Act · Art. 10 (Data Governance)` are
clickable. The UI opens a regulation detail modal with:

- article/control title
- summary and implementation detail
- applicable ethical dimensions
- source document link

The built-in framework data lives in `backend/app/data/frameworks.json`.

### Requirement Preferences

Each generated requirement can be marked:

- **Accept**: include it in the curated requirements set.
- **Reject**: record that the user does not want this requirement.
- **Clear from this chat**: suppress similar requirements in future Create
  responses for this chat.

For logged-in users, preferences are stored in
`chat_requirement_preferences`. For guests, they are stored in `sessionStorage`.
Suppressed requirements are injected into the prompt as per-chat preferences.
This is a prompt-level suppression mechanism, not yet embedding-based semantic
deduplication.

### Requirements Document Export

The `Generate Requirements Doc` button opens a preview modal before download.
The preview and downloaded `.docx` include:

- a link back to the chat (`?session=<id>`)
- the full first user prompt for that chat
- topic, persona and project context
- accepted requirements grouped by dimension
- guideline references

The DOCX builder is dependency-free and implemented in
`backend/app/services/docx_service.py`.

### Developer Mode

Developer Mode is available to logged-in users and is stored in
`localStorage('dev_mode')`. It includes:

- Prompt Inspector
- Raw Gemini response viewer
- Model/temperature/max-token overrides
- RAG Workspace
- Citation Audit
- Eval Harness

The RAG Workspace is currently **manual reference-document injection**:
uploaded `.md`, `.txt` and `.json` files are stored in browser localStorage and
prepended to LLM user content as `USER REFERENCE DOCS`. It does not yet use
embeddings, vector search or reranking.

### Auth

- Username/password login with JWT in `localStorage('access_token')`
- Google OAuth
- GitHub OAuth
- Guest mode without login

---

## Important API Surfaces

| Endpoint | Purpose |
|----------|---------|
| `POST /ethics/chat` | Auto-classify prompt and dispatch to Create/Validate/Compare |
| `GET /ethics/frameworks` | Built-in framework KB |
| `GET /ethics/findings` | Practitioner findings |
| `POST /chat/sessions` | Create logged-in chat session |
| `GET /chat/sessions` | List logged-in chat sessions |
| `PATCH /chat/sessions/{id}` | Edit session title/topic/topic prompt |
| `GET /chat/sessions/{id}/requirements` | List requirement preferences |
| `POST /chat/sessions/{id}/requirements` | Accept/reject/suppress a requirement |
| `GET /chat/sessions/{id}/requirements-doc-preview` | JSON preview for export modal |
| `GET /chat/sessions/{id}/requirements-doc` | Download accepted requirements as DOCX |

---

## Environment Variables

See [Docs/environment.md](Docs/environment.md) for the full reference.

Minimum production variables:

| Where | Variable |
|-------|----------|
| Render backend | `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `BACKEND_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, OAuth client IDs/secrets |
| Cloudflare Pages frontend | `VITE_API_BASE_URL` |

---

## Deployment

Deployment-specific services can be configured after review if needed.

```bash
cd backend && source venv/bin/activate && python -m pytest -q
cd ../frontend && npm run build
cd .. && git push origin main
```

Production health checks:

```bash
BASE=https://your-backend.example
curl "$BASE/health"
curl "$BASE/health/db"
```

Deployment notes live in [Docs/deployment.md](Docs/deployment.md).

---

## Troubleshooting

- Backend/API issues: [Docs/troubleshooting-backend.md](Docs/troubleshooting-backend.md)
- Database connectivity: [Docs/troubleshooting-database.md](Docs/troubleshooting-database.md)

---

## Research Context

This project supports the thesis methodology by operationalising a
triangulation workflow:

1. regulatory and framework guidance from EU AI Act and NIST AI RMF
2. real-world practitioner findings
3. LLM-assisted requirements engineering with explicit prompt grounding,
   persona adaptation and user curation

The current RAG capability is lightweight prompt grounding. A full production
RAG pipeline would add document ingestion, chunking, embeddings, vector search,
reranking and source-level citation management.

---

## License

Academic research artifact for anonymous peer review.
