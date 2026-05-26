# Anonymisation Notes

This artifact package is prepared for double-blind review.

## Removed Or Excluded

- Real `.env` files and deployment-only environment files.
- Gemini API keys.
- OAuth client secrets for Google and GitHub.
- PostgreSQL database URLs and JWT production secrets.
- Render and Cloudflare deployment tokens.
- Real user records, chat logs, raw survey responses, recordings and transcripts.
- Personal commit history is not required in the reviewer-facing repository.

## Included

- Source code needed to inspect and run the HealthAI Ethics Assistant.
- Placeholder environment examples only.
- Structured knowledge-base files.
- Prompt templates.
- Anonymised/aggregate evaluation materials sufficient to trace the paper's TAM
  and SUS claims.

## Before Uploading To GitHub

Run:

```bash
git status --short
git ls-files .env backend/.env frontend/.env.production
rg -n "(API_KEY|CLIENT_SECRET|SECRET_KEY|DATABASE_URL|TOKEN|PASSWORD)" .
```

The first command should not show private environment files staged for commit.
The search can show placeholder variable names, but it must not show real secret
values.
