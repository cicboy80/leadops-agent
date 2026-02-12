# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LeadOps Agent is a B2B agentic workflow system for automated lead intake, qualification, follow-up generation, and CRM-style activity logging. It uses LangGraph for pipeline orchestration and is designed for Azure deployment.

The system is an **agentic pipeline** (not a chatbot): CSV upload → normalize → enrich → score → decide → draft email → log to CRM. The pipeline has one branch point after the decision node (SEND_EMAIL/ASK_QUESTION → draft_email, DISQUALIFY/HOLD → log_to_crm).

## Architecture

- **Backend**: Python FastAPI (`/backend/app/`)
- **Orchestration**: LangGraph state machine (`/backend/app/graphs/`)
- **Frontend**: Next.js or React+Vite (`/frontend/`)
- **Database**: SQLite (local dev) or PostgreSQL (production/Azure)
- **IaC**: `/infra/` (Bicep or Terraform for Azure Container Apps)

### Backend Layer Separation

Three distinct model layers — never conflate them:
- `models/orm.py` — SQLAlchemy ORM models (database)
- `models/schemas.py` — Pydantic schemas (API request/response boundary)
- `graphs/state.py` — LangGraph state TypedDict (in-memory during graph execution)

Three logic layers:
- `api/` — Route handlers, validation, auth. Calls services only.
- `services/` — Business logic. Orchestrates repositories and graph invocation.
- `repositories/` or `db/` — Database access via SQLAlchemy. Returns ORM models.

Graph nodes must be thin wrappers (~5-10 lines) that call service methods. All business logic lives in `services/`, keeping it testable without LangGraph.

### LLM Integration

- LLM calls use `ChatOpenAI(...).with_structured_output(PydanticModel)` to enforce JSON schema via function calling
- All LLM output models live in `models/llm_schemas.py`: `ScoreResult`, `DecisionResult`, `EmailDraftResult`
- The system must work without an LLM key — deterministic/rule-based scoring is the fallback
- Provider configured via `LLM_PROVIDER=openai|azure_openai` env var

### Scoring System

Scoring weights are stored in a config (DB table or JSON file at `/data/scoring_config.json`). The "learning_update" node adjusts these weights based on outcome feedback using simple exponential moving average — this is NOT ML or model training.

## Build & Run Commands

```bash
make dev          # Run backend + frontend locally
make test         # Run all tests
make lint         # Lint backend + frontend
docker-compose up # Run full system in containers
```

```bash
# Backend only
cd backend && uvicorn app.main:app --reload --port 8000

# Run single test
cd backend && pytest tests/test_scoring.py -v
cd backend && pytest tests/test_scoring.py::test_hot_lead -v

# Seed demo data
python scripts/seed_demo_data.py
```

## Key Design Decisions

- CSV upload validates against injection (strip leading `=`, `+`, `-`, `@` from cells)
- PII redaction in traces: hash emails before storage. Free-text NER redaction is deferred.
- Email sending is always mock mode unless explicitly configured via env var
- All API endpoints require CORS configuration for the frontend domain (env-var driven, not wildcard)
- The spec at `/claude_prompt.md` is the canonical reference for data models, API endpoints, and LangGraph node definitions
