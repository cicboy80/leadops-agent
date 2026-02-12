# LeadOps Agent — Production-Ready Agentic AI for Lead Qualification & Follow-Up (LangGraph + Azure)

You are **Claude Code**. Build this repository as a **production-ready, end-to-end agentic workflow system** for automated lead intake, qualification, follow-up generation, and CRM-style activity logging — using **LangGraph** for orchestration. The system must be deployable on **Microsoft Azure** and include a **frontend UI**.

---

## 0) Product Goal (What we are building)

**LeadOps Agent** is a B2B workflow app that:
1. Ingests leads (CSV upload + manual entry)
2. Enriches them (light enrichment using open sources or heuristic enrichment; no scraping of LinkedIn)
3. Scores each lead **Hot / Warm / Cold** with **explanations**
4. Decides next action:
   - Send email (draft + approve in UI)
   - Ask clarifying question (draft + approve)
   - Disqualify (with reason)
5. Logs activities to a simple CRM-style database (lead timeline)
6. Learns from outcomes (human feedback + conversion labels) by updating scoring weights/rules and storing eval traces

This is **not a chatbot**. It is an **agentic pipeline**:
- multi-step reasoning
- tool-using agents
- deterministic data flows
- auditable traces
- robust error handling
- idempotent processing
- deployable on Azure

---

## 1) Non-Negotiable Requirements (Production Readiness)

### Architecture
- **Backend**: Python **FastAPI**
- **Orchestration**: **LangGraph** (state machine + nodes + conditional routing)
- **Storage**: Azure-friendly persistence:
  - Option A (preferred): **Azure Cosmos DB** (Mongo API) OR **PostgreSQL** (Azure Database for PostgreSQL)
  - Option B (local dev): SQLite
- **Queue / async**: Azure-ready background processing:
  - Option A: Azure Service Bus
  - Option B: FastAPI BackgroundTasks for MVP (include interface to upgrade to Service Bus)
- **Frontend UI**: **Next.js (TypeScript)** with a clean dashboard (or React + Vite if you must, but prefer Next.js)
- **Auth**: simple MVP auth (single-user token) + structured path for Azure Entra ID later
- **Observability**: structured logging + request IDs + LangGraph traces stored in DB
- **Config**: `.env` + Azure App Service env vars (no secrets in repo)
- **Deployment**: Azure App Service or Azure Container Apps (choose one and implement fully)
- **Containers**: Dockerfiles for backend and frontend; docker-compose for local
- **CI**: GitHub Actions workflow (lint/test/build)

### Quality
- Type hints (Python) and proper models (Pydantic)
- Deterministic JSON outputs from the agent (validated by Pydantic schemas)
- Retry logic around model/tool calls
- Robust input validation
- Clear separation: API layer vs domain logic vs graph
- Unit tests for scoring + routing + schema validation
- Golden-path demo dataset in `/data`

---

## 2) Core User Flows

### Flow A: Upload Leads (CSV)
- User uploads a CSV
- Backend validates and normalizes fields
- Leads are stored as `NEW`
- Graph runs per lead (sync for small batches, async for larger)
- UI shows processing status and results

### Flow B: Review & Approve
- UI shows lead detail
- UI shows:
  - score (Hot/Warm/Cold)
  - explanation
  - recommended action
  - drafted email (editable)
- User can:
  - Approve send
  - Edit then send
  - Mark as “needs more info” (agent drafts clarifying question)
  - Disqualify

### Flow C: Outcome Feedback
- User marks outcome:
  - `booked_demo`, `no_response`, `disqualified`, `closed_won`, `closed_lost`
- System updates lead status + stores feedback
- Learning node updates scoring weights/rules and stores evaluation trace

---

## 3) Data Model (Must Implement)

Use these entities (DB tables/collections). Keep it simple but real.

### Lead
- `id` (uuid)
- `first_name`, `last_name`
- `email`
- `company_name`
- `job_title`
- `industry`
- `company_size` (enum or int band)
- `country`
- `source` (enum: web_form, referral, outbound, event, partner)
- `budget_range` (string or enum)
- `pain_point` (string)
- `urgency` (enum: low/medium/high)
- `lead_message` (string)
- `status` (NEW, QUALIFIED, NEEDS_INFO, DISQUALIFIED, CONTACTED, MEETING_BOOKED, CLOSED_WON, CLOSED_LOST)
- `score_label` (HOT/WARM/COLD)
- `score_value` (0–100)
- `score_rationale` (string)
- `recommended_action` (SEND_EMAIL / ASK_QUESTION / DISQUALIFY / HOLD)
- timestamps: `created_at`, `updated_at`

### ActivityLog
- `id`, `lead_id`
- `type` (INGESTED, ENRICHED, SCORED, EMAIL_DRAFTED, EMAIL_SENT, STATUS_CHANGED, NOTE, ERROR)
- `payload` (json)
- `created_at`

### EmailDraft
- `id`, `lead_id`
- `subject`, `body`
- `variant` (first_touch, follow_up_1, follow_up_2, breakup)
- `approved` (bool)
- `sent_at` (nullable)

### Feedback
- `id`, `lead_id`
- `outcome`
- `notes`
- `created_at`

### Trace
- `id`, `lead_id`
- `graph_run_id`
- `node_events` (json)
- `llm_inputs` (redacted)
- `llm_outputs` (json)
- `created_at`

---

## 4) LangGraph Design (Must Implement)

Implement the graph with clear state and schemas.

### State Schema (Pydantic)
- `lead: Lead`
- `enrichment: dict`
- `score: ScoreResult`
- `decision: DecisionResult`
- `email_draft: EmailDraft | None`
- `errors: list[str]`
- `trace_id: str`

### Nodes
1. **normalize_input**
   - Validates and normalizes lead fields
2. **enrich_lead**
   - Uses heuristic enrichment + optional web search stub (OFF by default)
   - Must not scrape LinkedIn
3. **score_lead**
   - Produces `score_value`, `score_label`, `rationale`
   - Must output JSON matching Pydantic schema
4. **decide_next_action**
   - Based on score + missing fields
5. **draft_email**
   - Generates email subject/body variants
6. **log_to_crm**
   - Writes ActivityLog + updates Lead
7. **learning_update**
   - Updates a lightweight scoring config store (rules/weights) based on outcomes

### Conditional Routing
- If missing key info → ASK_QUESTION
- If low fit → DISQUALIFY
- If HOT/WARM → DRAFT_EMAIL

### Tooling
- Create a `tools/` module with interfaces:
  - `EmailTool` (mock sender + provider interface)
  - `CRMTool` (DB operations)
  - `EnrichmentTool` (heuristic + optional providers)
  - `ScoringConfigTool` (weights/rules persisted)

---

## 5) API (FastAPI) Endpoints (Must Implement)

### Leads
- `POST /api/leads` (create lead)
- `POST /api/leads/upload` (csv upload)
- `GET /api/leads` (list with filters)
- `GET /api/leads/{id}` (detail)
- `POST /api/leads/{id}/run` (run graph on lead)
- `POST /api/leads/{id}/status` (update status)
- `POST /api/leads/{id}/feedback` (store feedback)

### Drafts
- `GET /api/leads/{id}/drafts`
- `POST /api/leads/{id}/drafts` (create/update draft)
- `POST /api/leads/{id}/drafts/{draft_id}/approve_send`

### Activity / Traces
- `GET /api/leads/{id}/activity`
- `GET /api/leads/{id}/traces`

Add OpenAPI docs and ensure CORS is configured for the frontend domain.

---

## 6) Frontend UI (Must Implement)

Build a clean UI with these pages:

### `/`
**Dashboard**
- KPIs: total leads, hot/warm/cold counts, contacted, meetings booked
- Filterable leads table (status, score, source, date)

### `/leads/[id]`
**Lead Detail**
- Lead profile + enrichment
- Score + rationale
- Recommended action
- Draft email editor with approve/send button
- Activity timeline
- Feedback form

### `/settings`
- Configure scoring weights/rules (simple sliders or inputs)
- Toggle “web enrichment” ON/OFF
- Set email sender mode: mock vs provider

UI expectations:
- Polished, modern, responsive
- Uses server-side calls to backend
- Clear loading states and error handling

---

## 7) Deployment to Azure (Must Implement)

### Preferred Deployment Plan: **Azure Container Apps**
- One container for backend API
- One container for frontend
- Use Azure Container Registry (ACR)
- Use managed identity where possible
- App config via environment variables

Deliverables:
- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml` for local
- `/infra` folder with either:
  - Bicep templates OR
  - Terraform (pick one)
- A step-by-step `AZURE_DEPLOYMENT.md` including:
  - resource group creation
  - ACR build/push
  - Container Apps deploy
  - env var setup
  - database provisioning

Also include alternative quick path:
- Azure App Service for backend + Static Web Apps for frontend (optional)

---

## 8) Local Development (Must Implement)

Provide:
- `.env.example`
- `makefile` or `justfile` commands:
  - `make dev` (runs backend + frontend)
  - `make test`
  - `make lint`
- Seed script:
  - `python scripts/seed_demo_data.py` loads `/data/demo_leads.csv`

---

## 9) Demo Data (Must Provide)

Include:
- `/data/demo_leads.csv` with ~200 realistic leads
- `/data/demo_email_templates.json` with outreach variants
- A handful of “edge case” leads (missing email, ambiguous budget, etc.)

Leads must include diverse industries and realistic messages.

---

## 10) Security & Safety (Must Implement)

- Do not log secrets
- Redact PII in traces by default (store hashed email)
- Rate limit endpoints minimally
- Validate CSV upload to prevent injection
- Provide a “mock email mode” that never sends real mail unless configured

---

## 11) Testing (Must Implement)

Minimum tests:
- `test_scoring_schema_validation`
- `test_decision_routing`
- `test_csv_ingest_validation`
- `test_email_draft_schema`
- `test_api_smoke` (FastAPI test client)

---

## 12) Repo Structure (Use this)

/backend
/app
main.py
api/
core/
db/
graphs/
models/
tools/
services/
tests/
/frontend
...
/data
/infra
/scripts
AZURE_DEPLOYMENT.md
README.md
docker-compose.yml
.env.example


---

## 13) LLM Provider + Config

- Default to OpenAI-compatible API in backend (env var configurable)
- Must support:
  - `LLM_PROVIDER=openai|azure_openai`
  - `OPENAI_API_KEY` or Azure OpenAI vars
- Use structured outputs:
  - Force JSON schema for scoring/decision/email draft

---

## 14) Definition of Done (Checklist)

The build is complete when:
- `docker-compose up` runs the full system locally
- Upload CSV → leads processed → scores visible in UI
- Clicking a lead shows a drafted email with approve/send (mock mode)
- Feedback updates learning config
- Azure deployment doc is complete and reproducible
- Basic tests pass in CI
- README is strong and commercial

---

## 15) Now Start Building

Implement this repository end-to-end.

### Priority order
1. Backend models + DB + API
2. LangGraph orchestration + deterministic schemas
3. Frontend dashboard + lead detail + email editor
4. Demo data + seed scripts
5. Docker + local dev
6. Azure deployment + infra
7. Tests + CI

Do not leave TODOs. Choose sensible defaults, document assumptions, and make it run.

---