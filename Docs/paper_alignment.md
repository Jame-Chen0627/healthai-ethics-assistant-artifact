# Paper Alignment Checklist

This checklist maps the anonymous artifact package to the paper's description
of the HealthAI Ethics Assistant.

| Paper claim | Artifact evidence |
|---|---|
| Full-stack web application | `backend/` FastAPI API and `frontend/` Vue 3 SPA |
| Create-Validate-Compare workflow | `backend/app/services/ethics_service.py` and `frontend/src/components/cards/` |
| Auto-classification via `POST /ethics/chat` | `backend/app/routers/ethics.py` and `backend/app/services/ethics_service.py` |
| EU AI Act and NIST AI RMF encoded as structured JSON | `knowledge_base/eu_ai_act.json`, `knowledge_base/nist_ai_rmf.json`, `backend/app/data/frameworks.json` |
| Practitioner findings covering privacy, safety, bias, transparency and accountability | `knowledge_base/findings.json`, `backend/app/data/triangulation_findings.json` |
| Clickable regulatory references | `frontend/src/components/GuidelineRefBadge.vue` |
| Accept, Reject and Clear from this chat actions | `frontend/src/components/cards/CreateCard.vue` and `backend/app/routers/chat.py` |
| Accepted requirements exportable as `.docx` | `backend/app/services/docx_service.py` and `backend/app/routers/chat.py` |
| Three fixed personas plus a 20-question Let System Decide option | `frontend/src/components/NewChatModal.vue` |
| Lightweight document grounding in Developer Mode | `frontend/src/components/DevPanel.vue` and `backend/app/services/ethics_service.py` |
| Stack: FastAPI, SQLAlchemy 2, Pydantic v2, Python 3.11 | `backend/requirements.txt`, `backend/runtime.txt` |
| Stack: Vue 3, Vite, Vue Router | `frontend/package.json` |
| LLM: Google Gemini `gemini-2.5-flash` by default | `backend/app/config.py`, `backend/app/services/llm_service.py` |
| Storage: PostgreSQL in production, SQLite local | `backend/app/config.py`, `backend/app/database.py`, `Docs/environment.md` |
| Auth: JWT, Google OAuth, GitHub OAuth, guest mode | `backend/app/routers/auth.py`, `frontend/src/utils/guestSessions.js` |
| TAM and SUS evaluation values | `evaluation/anonymised_results.csv`, `evaluation/sus_calculation.csv`, `evaluation/tam_sus_questionnaire.md` |

Known limitation: the artifact includes the implementation and anonymised /
aggregate evaluation materials. It intentionally excludes raw participant
records, raw chat logs, recordings, transcripts, real environment files and
deployment secrets.
