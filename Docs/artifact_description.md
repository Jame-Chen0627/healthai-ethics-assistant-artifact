# Artifact Description

This repository is the replication package for the HealthAI Ethics Assistant,
a full-stack requirements-engineering web application for healthcare AI ethics.

## Main Components

- `backend/`: FastAPI API, authentication, chat/session storage, LLM integration,
  knowledge-base loading, and DOCX export.
- `frontend/`: Vue 3 + Vite single-page application implementing the
  Create-Validate-Compare workflow.
- `knowledge_base/`: Reviewer-facing copies of the encoded knowledge base:
  EU AI Act, NIST AI RMF, combined framework data, and practitioner findings.
- `prompts/`: Prompt templates corresponding to the Create, Validate and Compare
  modes.
- `evaluation/`: Anonymised TAM/SUS questionnaire materials and aggregate
  results used to support the paper's evaluation claims.
- `docs/`: Setup, anonymisation, deployment and troubleshooting notes.

## Workflow Evidence

- Create mode: `backend/app/services/ethics_service.py:create_requirements`
- Validate mode: `backend/app/services/ethics_service.py:validate_requirements`
- Compare mode: `backend/app/services/ethics_service.py:compare_scenarios`
- Auto-dispatch: `backend/app/services/ethics_service.py:classify_intent`
- UI rendering: `frontend/src/components/cards/`

## Knowledge Base Structure

Framework entries contain ids, framework names, article/control labels, titles,
summaries, implementation guidance, source links and applicable ethical
dimensions. Practitioner findings contain source, stakeholder group, ethical
dimension, anonymised/summarised concern text and requirement implication.
