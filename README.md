# Replication Package: HealthAI Ethics Assistant

**Paper:** AI Ethics to Requirements Practice: Building and Evaluating the HealthAI Ethics Assistant

**Artifact type:** Anonymous replication package for double-blind review

This package contains the implementation, structured knowledge base, prompt
templates, setup instructions, and anonymised evaluation materials for the
HealthAI Ethics Assistant described in the paper.

---

## Table of Contents

- [Overview](#overview)
- [Repository Contents](#repository-contents)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Expected Reviewer Checks](#expected-reviewer-checks)
- [Evaluation Materials](#evaluation-materials)
- [Paper Alignment](#paper-alignment)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

HealthAI Ethics Assistant is a full-stack web application that supports
healthcare AI requirements work through a structured
**Create-Validate-Compare** workflow.

**What this artifact provides:**

1. A FastAPI backend implementing authentication, chat sessions, grounded LLM
   calls, requirement preferences, and DOCX export.
2. A Vue 3 frontend implementing the practitioner-facing workflow, persona
   selection, requirement cards, clickable regulatory references, and Developer
   Mode document grounding.
3. A structured knowledge base covering EU AI Act entries, NIST AI RMF controls,
   and practitioner findings across privacy, safety, bias, transparency, and
   accountability.
4. Prompt templates for the Create, Validate, and Compare modes.
5. Anonymised/aggregate TAM and SUS evaluation materials corresponding to the
   results reported in the paper.

The package intentionally excludes real environment files, API keys, OAuth
secrets, deployment tokens, raw participant records, raw chat logs, recordings,
and transcripts.

---

## Repository Contents

```text
.
├── backend/                 FastAPI backend
│   ├── app/
│   │   ├── routers/         /auth, /ethics, /chat endpoints
│   │   ├── services/        LLM orchestration and DOCX export
│   │   └── data/            Runtime framework and findings JSON
│   ├── tests/               Backend tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/                Vue 3 + Vite frontend
│   ├── src/components/      Chat UI, cards, persona modal, Developer Mode
│   ├── src/views/
│   ├── package.json
│   └── .env.example
├── knowledge_base/          Reviewer-facing knowledge-base files
├── prompts/                 Create, Validate, Compare prompt templates
├── evaluation/              TAM/SUS questionnaire and aggregate results
├── Docs/                    Setup, anonymisation, deployment, alignment notes
└── README.md
```

Key alignment file:

```text
Docs/paper_alignment.md
```

This maps paper claims to concrete files in the artifact.

---

## Requirements

- **Python:** 3.11
- **Node.js:** 20 or higher
- **Package managers:** `pip`, `npm`
- **Storage:** Less than 100 MB after dependency installation, excluding
  virtual environments and `node_modules`
- **Network:** Required only for dependency installation and live Gemini calls
- **LLM key:** Google Gemini API key for live Create/Validate/Compare responses

Reviewers can inspect the code, knowledge base, prompt templates, tests, and
evaluation files without a Gemini key. A key is only needed to run live LLM
generation.

---

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and set at least:

```env
DATABASE_URL=sqlite:///./app.db
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=change_me
CORS_ORIGINS=["http://localhost:5173"]
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Run the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

Backend API docs are available at:

```text
http://localhost:8000/docs
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open:

```text
http://localhost:5173
```

---

## Configuration

### Backend Environment Variables

| Variable | Local value | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./app.db` | Local SQLite database |
| `GEMINI_API_KEY` | `your_api_key_here` | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Default LLM model |
| `SECRET_KEY` | `change_me` | JWT signing secret for local review |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed frontend origins |
| `BACKEND_URL` | `http://localhost:8000` | Backend base URL |
| `FRONTEND_URL` | `http://localhost:5173` | Frontend base URL |

OAuth variables are optional for local review. Guest mode and username/password
auth can be used without Google or GitHub OAuth credentials.

### Frontend Environment Variables

| Variable | Local value | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

---

## Usage

### Basic Workflow

1. Start the backend and frontend using the commands above.
2. Open `http://localhost:5173`.
3. Continue as guest or create a local account.
4. Click **New Chat**.
5. Select the HealthAI Ethics topic.
6. Choose a persona:
   - Healthcare Professional
   - Software Engineer
   - Healthcare Researcher
   - Let System Decide, which uses a 20-question mixed-persona questionnaire
7. Try one of the three workflow modes:
   - **Create:** ask for ethical requirements for a healthcare AI scenario.
   - **Validate:** provide an existing requirement and ask whether it is
     compliant or complete.
   - **Compare:** provide a draft requirement and ask how it compares with
     practitioner concerns.

The backend classifies free-form messages through:

```text
POST /ethics/chat
```

### Example Prompts

Create:

```text
We are building a CT-scan triage AI. What privacy and safety requirements should we consider?
```

Validate:

```text
Validate this requirement: The system shall log all AI triage recommendations and clinician overrides.
```

Compare:

```text
Compare this requirement with real-world practitioner concerns: The model shall explain why each patient was prioritised.
```

### Developer Mode Document Grounding

Developer Mode includes a lightweight document-grounding workspace. Reviewers
can upload `.md`, `.txt`, or `.json` reference documents. Their content is
prepended to the LLM prompt as additional context. This is intentionally
lightweight prompt grounding, not a vector-search RAG pipeline.

---

## Expected Reviewer Checks

### Run Backend Tests

```bash
cd backend
source venv/bin/activate
python -m pytest -q
```

Expected result:

```text
6 passed
```

### Build Frontend

```bash
cd frontend
npm run build
```

Expected result:

```text
✓ built
```

### Inspect Knowledge Base

The reviewer-facing knowledge base is in:

```text
knowledge_base/
├── eu_ai_act.json
├── nist_ai_rmf.json
├── frameworks.json
└── findings.json
```

The runtime copies used by the backend are:

```text
backend/app/data/frameworks.json
backend/app/data/triangulation_findings.json
```

---

## Evaluation Materials

Evaluation files are in:

```text
evaluation/
├── tam_sus_questionnaire.md
├── anonymised_results.csv
└── sus_calculation.csv
```

These files include the anonymised/aggregate TAM and SUS values reported in the
paper. Raw participant identifiers, raw survey forms, recordings, transcripts,
and raw chat logs are excluded for anonymisation and ethics reasons.

Reported paper values represented in this package include:

- SUS total score: 60
- TAM Q10, "Traceable references increased trust": 5
- TAM Table 2 values for Q1, Q2, Q4-Q8, Q10 and Q11

---

## Paper Alignment

For a claim-by-claim mapping from the paper to artifact files, see:

```text
Docs/paper_alignment.md
```

Examples:

| Paper claim | Artifact evidence |
|---|---|
| Create-Validate-Compare workflow | `backend/app/services/ethics_service.py`, `frontend/src/components/cards/` |
| Auto-classification via `/ethics/chat` | `backend/app/routers/ethics.py` |
| EU AI Act and NIST AI RMF as structured JSON | `knowledge_base/eu_ai_act.json`, `knowledge_base/nist_ai_rmf.json` |
| Practitioner findings in five ethical dimensions | `knowledge_base/findings.json` |
| DOCX export for accepted requirements | `backend/app/services/docx_service.py` |

---

## Troubleshooting

### Backend cannot start

Check that dependencies are installed and the virtual environment is active:

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### `GEMINI_API_KEY` error

Live LLM calls require a valid Gemini API key in `backend/.env`:

```env
GEMINI_API_KEY=your_api_key_here
```

Without a valid key, the code and tests can still be inspected, but live
generation will fail.

### CORS error in browser

Ensure `backend/.env` contains:

```env
CORS_ORIGINS=["http://localhost:5173"]
```

Then restart the backend.

### Frontend cannot reach backend

Ensure `frontend/.env` contains:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Then restart `npm run dev`.

### Different LLM output than paper screenshots

This is expected. Live Gemini responses may vary over time. The reproducible
parts of this package are the implementation, workflow structure, knowledge
base, prompt templates, and anonymised evaluation materials.

---

## License

This artifact is provided for academic peer review and research replication.
No real secrets, raw participant records, raw chat logs, or deployment
credentials are included.
