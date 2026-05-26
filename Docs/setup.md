# Setup

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

For local review, `DATABASE_URL=sqlite:///./app.db` is sufficient. A Gemini API
key is required for live LLM calls. Without a valid key, reviewers can still
inspect the code, knowledge base, prompt templates and tests.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` when `VITE_API_BASE_URL` is not
set. Open `http://localhost:5173` after both services are running.

## Checks

```bash
cd backend
python -m pytest -q

cd ../frontend
npm run build
```
