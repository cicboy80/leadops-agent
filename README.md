# LeadOps Agent

B2B agentic workflow system for automated lead intake, qualification, follow-up generation, and CRM-style activity logging.

## What It Does

1. **Ingests leads** via CSV upload or manual entry
2. **Enriches** leads with heuristic data (email domain analysis, company type inference)
3. **Scores** each lead HOT / WARM / COLD with explanations (LLM-powered or rule-based fallback)
4. **Decides** next action: send email, ask clarifying question, disqualify, or hold
5. **Drafts emails** using LLM with approve/edit/send workflow in UI
6. **Logs activities** to a CRM-style timeline per lead
7. **Learns** from outcome feedback by adjusting scoring weights

## Architecture

- **Backend**: Python FastAPI + SQLAlchemy 2.0 async
- **Orchestration**: LangGraph state machine with PostgreSQL checkpointing
- **Database**: PostgreSQL 16
- **Frontend**: Next.js 14 App Router + Tailwind CSS
- **LLM**: OpenAI (gpt-4o-mini for scoring/decisions, gpt-4o for email drafting)
- **Deployment**: Azure Container Apps via Bicep IaC

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- OpenAI API key (optional — system works with rule-based fallback)

### Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your OPENAI_API_KEY (optional)

# Start Postgres + backend + frontend
docker-compose up

# Or run locally:
make dev
```

### Database Setup

```bash
# Run migrations
make migrate

# Seed demo data
make seed
```

### Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## API Endpoints

All endpoints under `/api/v1/`:

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /leads | Create lead |
| POST | /leads/upload | CSV upload |
| GET | /leads | List leads (paginated) |
| GET | /leads/{id} | Lead detail |
| POST | /leads/{id}/run | Run pipeline on lead |
| POST | /leads/{id}/status | Update lead status |
| POST | /leads/{id}/feedback | Submit feedback |
| POST | /leads/bulk-run | Run pipeline on multiple leads |
| GET | /leads/{id}/drafts | List email drafts |
| POST | /leads/{id}/drafts | Create draft |
| POST | /leads/{id}/drafts/{draft_id}/approve_send | Approve & send |
| GET | /leads/{id}/activity | Activity timeline |
| GET | /leads/{id}/traces | Pipeline traces |
| GET | /settings/scoring-config | Get scoring config |
| PUT | /settings/scoring-config | Update scoring config |
| GET | /leads/processing-stream | SSE progress stream |

## Pipeline Flow

```
CSV Upload → normalize_input → enrich_lead → score_lead → decide_next_action
                                                              ↓
                                          ┌─────────────────────────────────┐
                                          │ SEND_EMAIL/ASK_QUESTION         │
                                          │   → draft_email → log_to_crm   │
                                          │ DISQUALIFY/HOLD                 │
                                          │   → log_to_crm                  │
                                          └─────────────────────────────────┘
```

## Development

```bash
make test       # Run all tests
make lint       # Lint backend + frontend
make format     # Auto-format code
make migrate    # Run DB migrations
```

## Deployment

See [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) for Azure Container Apps deployment guide.

```bash
make deploy     # Build, push, and deploy to Azure
```

## Project Structure

```
backend/
  app/
    api/v1/          # FastAPI route handlers
    core/            # Config, database, auth, logging, LLM client
    graphs/          # LangGraph pipeline and nodes
    middleware/      # Correlation IDs, error handling
    models/          # ORM, schemas, graph state, LLM schemas
    repositories/    # Database access layer
    services/        # Business logic
    tools/           # Email, CRM, enrichment, scoring tools
  alembic/           # Database migrations
  tests/             # Unit and integration tests
frontend/
  src/
    app/             # Next.js pages
    components/      # React components
    lib/             # API client, types
    hooks/           # Custom hooks (SSE)
data/                # Demo data (CSV, templates)
infra/               # Bicep IaC modules
scripts/             # Seed and utility scripts
```
