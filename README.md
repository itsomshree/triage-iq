# TriageIQ

An AI-powered support ticket triage engine that classifies, routes, auto-answers, and escalates incoming tickets end-to-end – with grounded RAG responses and real tool-calling side effects, not just chat. It's a hands-on build covering structured LLM output, a working retrieval pipeline, tool calling, and prompt engineering driven by an evaluation harness, deployed and hardened as a real, publicly reachable service rather than left as a local notebook.

**🔗 Live demo:** [triage-iq.onrender.com](https://triage-iq.onrender.com) – opens straight into the ops dashboard, pre-loaded with sample tickets. It's kept warm by automated health checks, so there's no cold-start wait.

---

## Architecture

```
Incoming Ticket
      │
      ▼
[1] Classification Chain ──▶ Pydantic: category, urgency, summary, confidence
      │
      ▼
[2] Routing Chain (rule-based on classifier output)
      │
   ┌──┼────────────────────┐
   ▼  ▼                    ▼
Auto-Answer            Escalate              Flag for Review
(RAG chain)            (tool calling)         (no further action)
   │                      │
   ▼                      ▼
Retrieve from          escalate_ticket tool
Pinecone KB,           → decide team/priority
compress + generate    create_trello_card tool
answer, check          → real Trello API call
groundedness              │
   │                      │
   └──────────┬───────────┘
              ▼
      Structured Final Response
              │
              ▼
   Persisted to Postgres (ticket, classification,
   routing decision, RAG answer, escalation, stage logs)
   + returned via FastAPI + visible on the ops dashboard
```

**Key routing behavior:** if a ticket is routed to auto-answer but the RAG chain can't produce a *grounded* answer, the pipeline overrides the routing decision to `escalate` rather than surfacing an unsupported answer – a deliberate precision-over-recall tradeoff (see [Limitations](#limitations--tradeoffs)).

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Orchestration | LangChain (chains, retrievers, tool calling) | Composable pipeline with typed hand-offs between stages |
| LLM | Groq-hosted open-source model | Fast, low-cost inference for iterating quickly on prompts |
| Embeddings | HuggingFace `sentence-transformers` (local, CPU) | No embedding API cost or dependency |
| Vector store | Pinecone | Managed similarity search over the knowledge base |
| Relational store | PostgreSQL (Supabase) via SQLAlchemy | Tickets, classifications, routing decisions, escalations, structured logs |
| Structured output | Pydantic | Schema-enforced output at every pipeline stage |
| Tool calling / side effects | LangChain `@tool` + Trello REST API | Escalation actually creates a trackable, assigned card |
| API layer | FastAPI + `slowapi` rate limiting | Serves the pipeline as a real, abuse-resistant HTTP service |
| Ops visibility | Static dashboard served by the API | Live view of routing mix, accuracy, and per-ticket pipeline traces |
| Hosting | Render (free tier) | Public deployment target with real, non-negotiable resource limits |
| Package management | `uv` | Fast, modern dependency + venv management |

---

## Prompt engineering example

The classifier prompt doesn't just list category/urgency definitions – it includes worked examples at the two boundaries that were hardest to get right, added after reviewing evaluation mismatches:

1. **Shipping vs. general inquiry**: a question about *this specific shipment* (cost, timing, redirect) is `shipping`; the same policy question applied to an order that hasn't shipped yet (e.g. "can I still cancel?") is `general_inquiry`, because nothing is in transit yet.
2. **Medium vs. high urgency**: a damaged item with no time pressure ("whenever you get a chance") is `medium`; the same damaged item tied to a dollar amount *and* a deadline is `high` – urgency is driven by stakes and time pressure, not by whether something broke.

Each boundary includes a contrasting pair of tickets with the reasoning spelled out, rather than relying on the model to infer the distinction from category definitions alone.

---

## Evaluation results

Run via `uv run python scripts/run_eval.py` against a 27-ticket labeled set (`data/eval_set.json`):

| Metric | Result |
|---|---|
| Category accuracy | 92.6% (25/27) |
| Urgency accuracy | 88.9% (24/27) |
| Routing action accuracy | 96.3% (26/27) |
| Pipeline failures | 1/27 (LLM provider rate limit, not a logic error) |

The one category miss and both urgency misses cluster at genuinely ambiguous boundary cases – exactly the kind of failure the eval harness exists to surface, and what the few-shot prompt examples above were added to correct.

---

## Shipping it: deployment engineering

- Deployed the FastAPI + RAG pipeline on a free-tier cloud host and resolved production issues that did not appear in local development, including startup timeouts, memory growth, and database connectivity failures.
- Improved reliability by lazy-loading heavy ML dependencies, caching the embeddings client as a singleton, and migrating to an IPv4-compatible database pooler with properly encoded credentials.
- Diagnosed deployment failures through import-chain isolation and profiling, identifying memory pressure and inefficient initialization as root causes.
- Reduced end-to-end auto-answer latency from **~79s to 3.8s** through model caching and retrieval optimization.
- Secured the public deployment with server-side rate limiting and omitted write-enabled Trello credentials to prevent abuse of external services.

---

## Ops dashboard

The dashboard (served at `/dashboard`, and at the root URL via redirect) shows, live:
- Routing mix (auto-answer / escalate / flag-for-review) as a donut chart
- Category and urgency breakdowns
- Average classifier confidence and end-to-end pipeline latency
- A searchable recent-tickets table – click any row to see the full per-stage pipeline trace (classification → routing → RAG/escalation) for that ticket

It reads from the same structured logs (`pipeline_logs` table) that every real run writes to, so it reflects actual pipeline behavior, not mocked data.

---

## Project structure

```
triage-iq/
├── render.yaml                  # Render Blueprint deployment config
├── src/triage_iq/
│   ├── config.py                # env-driven configuration
│   ├── schemas/                 # Pydantic models for every pipeline stage
│   ├── chains/                  # classifier, routing, RAG, escalation chains
│   ├── tools/                   # LangChain @tool: escalate_ticket, create_trello_card
│   ├── retrievers/              # contextual compression retriever over Pinecone
│   ├── ingestion/                # KB loading, chunking, embedding + upsert
│   ├── db/                      # SQLAlchemy models + CRUD
│   ├── integrations/            # Trello REST client
│   └── pipeline.py              # run_ticket(): ties every stage together
├── api/                         # FastAPI app + dashboard
├── scripts/                     # init_db, ingest_knowledge_base, run_eval, seed_demo_data
├── data/                        # knowledge base docs, sample tickets, labeled eval set
└── tests/                       # unit + integration tests per module
```

---

## Setup & quickstart (local)

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# fill in GROQ_API_KEY, PINECONE_API_KEY, SUPABASE_URL/KEY, DATABASE_URL
# TRELLO_API_KEY / TRELLO_API_TOKEN are optional — escalation still records
# to Postgres without them, it just won't create a Trello card

# 3. Create database tables
uv run python scripts/init_db.py

# 4. Embed and upload the knowledge base
uv run python scripts/ingest_knowledge_base.py

# 5. Run the API
uv run uvicorn api.main:app --reload
# dashboard: http://localhost:8000/dashboard

# 6. (Optional) seed sample data to see the dashboard populated
uv run python scripts/seed_demo_data.py

# 7. Run the evaluation suite
uv run python scripts/run_eval.py

# 8. Run tests
uv run pytest
```

## Deployment

The included `render.yaml` deploys the app as a Render Blueprint – one web service serving both the API and the dashboard. Required secrets (`GROQ_API_KEY`, `PINECONE_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`) are entered at deploy time and never committed; `APP_BASE_URL` is set post-deploy once Render assigns the live URL.

---

## Limitations & Tradeoffs

- Dependent on free-tier, rate-limited LLM endpoints; transient classification failures can occur under load and are surfaced explicitly rather than silently ignored.
- Designed around the compute and memory constraints of a free-tier deployment, requiring lazy loading, caching, and reduced retrieval depth to maintain acceptable latency.
- Prioritizes grounded responses over coverage: when retrieved context is insufficient, the system escalates rather than generating potentially incorrect answers.
- Processes each ticket independently and does not maintain conversational context across a customer's ticket history or follow-up interactions.
- Retrieval quality is constrained by knowledge-base coverage; unsupported or poorly represented topics cannot be reliably answered even when correctly classified.
- Uses CPU-only embedding generation, which is adequate for the current scale but slower than a production-grade GPU-backed deployment.

---

## Possible extensions

- Multi-query retrieval alongside contextual compression, compared on the same eval set
- Swap the escalation sink to Linear/Jira as an alternative to Trello
- A/B test model size (8B vs. 70B) on the eval set for an accuracy/latency/cost tradeoff writeup
- Conversation-level memory for tickets with follow-up messages