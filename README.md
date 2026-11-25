---
title: NexusCore AI
emoji: 🛡️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# NexusCore AI — Enterprise Supply Chain Intelligence & Resilience Platform

**NexusCore AI** is an end-to-end enterprise supply chain risk intelligence and decision-orchestration platform that integrates **Medallion Data Engineering**, **Hybrid GraphRAG (NetworkX + Qdrant Cloud)**, **Predictive Machine Learning (XGBoost + MLflow)**, **1,000-Iteration Monte Carlo Risk Simulation**, **Parallel Multi-Agent Orchestration (LangGraph)**, and **Human-in-the-Loop (HITL) Governance** backed by a **SHA-256 hash-chained audit ledger**.

Instead of relying on an LLM to guess operational metrics or approve high-risk financial actions autonomously, NexusCore AI separates deterministic quantitative computation from generative reasoning—tracing multi-hop supplier dependencies, forecasting warehouse stockouts, verifying debt covenant compliance (`COV-FIN-01`), and streaming audited executive briefs in real time.

## Key Capabilities & System Architecture

```text
[Raw Enterprise CSVs & Corporate Policy JSON]
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. Medallion Data Engineering & Quality Gate (app/data_eng)                              │
│    • Schema validation + Dead-Letter Queue (data/dlq/shipments_dlq.json)                 │
│    • Cleaned & Curated Parquet Marts (data/curated/inventory_risk_mart.parquet)          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────────┐ ┌──────────────────────────────────────────────────────────────────┐
│ 2. Predictive ML    │ │ 3. Hybrid GraphRAG Engine (app/kg & app/rag)                     │
│    (app/ml)         │ │    • NetworkX directed KG + PageRank bottleneck centrality       │
│    • XGBoost delay  │ │    • Qdrant Cloud Dense + BM25 Reciprocal Rank Fusion (RRF)      │
│      & stockout     │ │      across SOPs, tariff rules & debt covenants                  │
│    • MLflow registry│ │    • Tenant-isolated semantic query cache (NexusCore-Cache)      │
└─────────────────────┘ └──────────────────────────────────────────────────────────────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. Parallel Multi-Agent Swarm (LangGraph Send API + SSE Streaming)                       │
│    • Meta-Planner Agent ──▶ Dispatches 3 specialist workers in parallel:                 │
│      [Graph Investigator]   [ML & SQL Data Scientist]   [Risk & Compliance Auditor]      │
│    • Adversarial Red-Team Critic ──▶ Audits numerical & policy consistency               │
│    • Executive Synthesizer ──▶ Decision brief, Cytoscape subgraph & Chart.js insights    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 5. Governance, RBAC & HITL Control Layer (app/security & app/sim)                        │
│    • Prompt/SQL injection guardrails & tenant scope isolation (GOV-SEC-01)               │
│    • 1,000-iteration Monte Carlo cost & COV-FIN-01 (28.0% margin floor) simulator        │
│    • Auto-escalation (> USD 50,000) to SupplyChainDirector HITL approval queue           │
│    • Tamper-evident SHA-256 hash-chained audit ledger (Supabase PostgreSQL / SQLite)     │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Core Engineering Layers

1. **Medallion ETL & Dead-Letter Queue (`app/data_eng/`):**
   - Ingests raw ERP and logistics datasets (`suppliers.csv`, `components.csv`, `bom.csv`, `inventory.csv`, `products.csv`, `shipments_history.csv`), quarantines malformed rows into `data/dlq/shipments_dlq.json`, and builds curated Parquet analytics marts (`data/curated/inventory_risk_mart.parquet`).
2. **Hybrid GraphRAG Engine (`app/kg/` & `app/rag/`):**
   - Resolves canonical entities (`SUP-*`, `CMP-*`, `PRD-*`, `PORT-*`, `POL-*`, `REG-*`) into a directed **NetworkX** knowledge graph (`data/curated/kg_snapshot.json`) with **PageRank** centrality scoring, fused via **Reciprocal Rank Fusion (RRF)** with dense embeddings and sparse lexical vectors (`BM25`) in **Qdrant Cloud**.
3. **Predictive ML & Stochastic Simulation (`app/ml/` & `app/sim/`):**
   - Uses trained **XGBoost** classifiers and regressors (`models_registry/*.joblib`, tracked via **MLflow**) to forecast supplier delay and `WH-ID` stockout probabilities, feeding a **1,000-iteration Monte Carlo** engine (`monte_carlo.py` & `optimizer.py`) that computes P50 median cost, P95 Value-at-Risk (VaR), and `COV-FIN-01` gross margin (`28.0%`) compliance.
4. **Parallel Multi-Agent Swarm & Multi-Provider Routing (`app/agents/` & `app/core/`):**
   - Coordinates six LangGraph nodes over Server-Sent Events (`POST /api/investigate/stream`), routing LLM inference across **Google Gemini** and **Groq** with automatic failover, Qdrant semantic caching (`semantic_cache.py`), and **Langfuse** tracing.
5. **Security Guardrails, RBAC & Audit Ledger (`app/security/`):**
   - Enforces tenant isolation (`GOV-SEC-01`) and prompt/SQL injection filtering (`guardrails.py`), locks mitigation actions above `USD 50,000` for `SupplyChainDirector` / `Admin` approval (`audit_hitl.py`), and records every event in a verifiable **SHA-256 hash chain**.
6. **Dual-Persona Enterprise SaaS Interface (`frontend/`):**
   - **Executive View:** Operational risk alerts, live KPI cards, structured _Executive Decision Briefs_ with progressive disclosure accordions, and data-driven **Chart.js** visual insights.
   - **Engineering View:** Real-time LangGraph stage telemetry, per-worker latency, NetworkX multi-hop reasoning paths, RRF retrieval scores, and XGBoost risk tables.
   - **Supply Chain Graph Explorer & What-If Simulator:** Interactive **Cytoscape.js** dependency explorer with on-demand edge labels and 1-hop neighborhood highlighting, paired with a custom Monte Carlo parameter simulator.

## Project Structure

```text
nexuscore-ai/
├── app/
│   ├── agents/
│   │   ├── state.py              # TypedDict state schema for LangGraph parallel swarm
│   │   └── swarm.py              # 6-node LangGraph Send-API workflow & SSE trace emitter
│   ├── api/
│   │   ├── routes.py             # FastAPI endpoints, SSE streaming, simulation & HITL routes
│   │   └── schemas.py            # Strict Pydantic request/response contracts
│   ├── core/
│   │   ├── bootstrap_infra.py    # Startup initialization & infrastructure bootstrap
│   │   ├── config.py             # Pydantic settings & environment configuration
│   │   ├── database.py           # SQLAlchemy engine & Supabase PostgreSQL / SQLite session
│   │   ├── llm_router.py         # Multi-provider LLM router (Gemini + Groq) & Langfuse tracing
│   │   ├── semantic_cache.py     # Qdrant-backed tenant-isolated semantic query cache
│   │   └── vector_store.py       # Qdrant Cloud hybrid Dense + Sparse vector client
│   ├── data_eng/
│   │   ├── etl_pipeline.py       # Medallion ETL pipeline (raw CSV -> cleaned -> curated Parquet)
│   │   ├── quality_gate.py       # Schema validation & Dead-Letter Queue (DLQ) quarantine
│   │   └── stream_simulator.py   # Logistics telemetry & port congestion event simulator
│   ├── kg/
│   │   ├── entity_resolver.py    # Canonical entity resolution across structured & text sources
│   │   └── extractor.py          # Knowledge Graph triple extraction & snapshot builder
│   ├── mcp/
│   │   └── server.py             # Model Context Protocol (MCP) server for enterprise tools
│   ├── ml/
│   │   ├── features.py           # Supply chain & lead-time feature engineering
│   │   ├── predictor.py          # XGBoost delay & stockout inference engine
│   │   └── train_models.py       # Model training & MLflow artifact registration
│   ├── rag/
│   │   ├── graph_engine.py       # NetworkX multi-hop traversal & PageRank centrality engine
│   │   ├── hybrid_graphrag.py    # Reciprocal Rank Fusion (Dense + BM25 + Graph context)
│   │   └── indexer.py            # Enterprise SOP/contract chunking & Qdrant indexing
│   ├── security/
│   │   ├── audit_hitl.py         # SHA-256 hash-chained audit ledger & HITL ticket manager
│   │   ├── guardrails.py         # Prompt/SQL injection detection & tenant/RBAC enforcement
│   │   └── secured_runner.py     # Policy-wrapped execution runner
│   ├── sim/
│   │   ├── monte_carlo.py        # 1,000-iteration stochastic cost & COV-FIN-01 simulator
│   │   └── optimizer.py          # Multi-strategy mitigation utility optimizer
│   └── main.py                   # FastAPI entrypoint, lifespan setup & static frontend mount
├── data/
│   ├── cleaned/                  # Validated Parquet tables (bom, components, inventory, etc.)
│   ├── curated/                  # Curated marts (inventory_risk_mart.parquet, kg_snapshot.json)
│   ├── dlq/                      # Data quality reports & quarantined shipment records
│   ├── documents/                # Enterprise policies, covenants & contracts (corp_docs.json)
│   ├── raw/                      # Synthetic enterprise CSV source tables
│   ├── generate_enterprise_data.py
│   └── golden_dataset.json
├── docs/
│   └── ARCHITECTURE.md           # Detailed system architecture specification
├── frontend/
│   ├── app.js                    # SSE client, Cytoscape.js explorer, Chart.js dynamic insights
│   ├── index.html                # Dual-persona Light-First Enterprise SaaS UI
│   └── styles.css                # Minimalist design system tokens & responsive layout
├── models_registry/              # Trained Joblib artifacts & SQLite MLflow tracking store
├── tests/
│   ├── __init__.py
│   └── test_nexuscore_e2e.py     # End-to-end Pytest evaluation & regression suite
├── .dockerignore
├── .env.example
├── Dockerfile                    # Hugging Face Spaces (port 7860, UID 1000) & container build
├── README.md
└── requirements.txt
```

## API Endpoints

| Method | Endpoint                                | Description                                                                                                                                  |
| :----- | :-------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/`                                     | Serves the interactive **NexusCore AI** Light-First web interface.                                                                           |
| `GET`  | `/docs`                                 | Interactive Swagger / OpenAPI documentation.                                                                                                 |
| `GET`  | `/api/health`                           | Verifies service health, database connectivity, and runtime readiness.                                                                       |
| `GET`  | `/api/overview`                         | Returns KPIs, `WH-ID` inventory risk predictions, PageRank bottlenecks, initial Cytoscape graph, HITL queue, and SHA-256 audit chain status. |
| `POST` | `/api/investigate/stream`               | Streams real-time LangGraph multi-agent execution events via Server-Sent Events (SSE) and returns the verified decision brief.               |
| `POST` | `/api/simulate`                         | Runs a custom 1,000-iteration Monte Carlo simulation and evaluates `COV-FIN-01` gross margin resilience.                                     |
| `POST` | `/api/hitl/tickets/{ticket_id}/resolve` | Enforces RBAC (`SupplyChainDirector` / `Admin`) to approve or reject pending high-value mitigation tickets.                                  |

## Automated Testing & Regression Suite (`pytest -v`)

All **5/5 automated end-to-end tests** in `tests/test_nexuscore_e2e.py` pass:

| Test Case                                        | Verification Scope                                                                                                                                               | Status   |
| :----------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------- |
| `test_01_frontend_static_assets_served`          | Verifies `/`, `/static/styles.css`, and `/static/app.js` return `HTTP 200`.                                                                                      | `PASSED` |
| `test_02_overview_and_tenant_isolation`          | Verifies KPIs, `WH-ID` risk marts, valid SHA-256 chain, and `HTTP 403` rejection on unauthorized tenants.                                                        | `PASSED` |
| `test_03_monte_carlo_what_if_simulator`          | Validates 1,000-iteration Monte Carlo P50/P95 percentiles, histogram bins, and `COV-FIN-01` margin analysis.                                                     | `PASSED` |
| `test_04_prompt_injection_guardrail_and_audit`   | Confirms prompt/SQL injection attempts are blocked (`HTTP 400/403`) while preserving audit chain integrity.                                                      | `PASSED` |
| `test_05_multi_agent_sse_and_hitl_rbac_workflow` | Tests full LangGraph SSE streaming, strategy optimization, `Analyst` (`403`) vs. `SupplyChainDirector` (`200`) RBAC enforcement, and final SHA-256 verification. | `PASSED` |

## Local Setup & Quickstart

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/4gnim/nexuscore-ai.git
cd nexuscore-ai
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials (local deterministic fallbacks remain active if cloud LLM or Qdrant credentials are omitted):

```env
APP_NAME="NexusCore AI"
APP_ENV=development
DEFAULT_TENANT_ID=TENANT-APEX-GLOBAL

GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here

SUPABASE_DB_URL="postgresql://postgres.xxxx:%23your_password@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

QDRANT_URL=https://your-cluster-id.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_DOCS_COLLECTION=NexusCore-Docs
QDRANT_CACHE_COLLECTION=NexusCore-Cache

MLFLOW_TRACKING_URI=sqlite:///models_registry/mlflow.db

LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

JWT_SECRET_KEY=nexuscore-enterprise-secret-2026
APPROVAL_FINANCIAL_THRESHOLD_USD=50000
RATE_LIMIT_PER_MINUTE=25
```

### 3. Run Automated Tests & Start Server

```bash
pytest -v
uvicorn app.main:app --reload --port 7860
```

Open **`http://127.0.0.1:7860`** in your browser to access the dashboard or **`http://127.0.0.1:7860/docs`** for the OpenAPI specification.

## Hugging Face Spaces Deployment (`sdk: docker`)

This repository is configured to run directly on **Hugging Face Spaces** using the **Docker SDK** (`sdk: docker`, `app_port: 7860`) with a non-root runtime user (`UID 1000`) and pre-cached FastEmbed ONNX models:

1. Open your Space **Settings** on Hugging Face and set **Space hardware** to `CPU basic (2 vCPU · 16 GB RAM · Free)`.
2. Add your `.env` credentials (`GEMINI_API_KEY`, `GROQ_API_KEY`, `SUPABASE_DB_URL`, `QDRANT_URL`, `QDRANT_API_KEY`, etc.) under **Variables and secrets**.
3. Push this repository to the Space remote (`git push --force hf main`) to trigger the container build and launch the FastAPI server on port `7860`.

## Limitations & Scope

- **Simulated Enterprise Dataset:** All suppliers, components, shipments, contracts, and financial baselines represent simulated data for _ApexGlobal Manufacturing Corp_ designed to demonstrate end-to-end AI systems engineering.
- **Demo Session Role Switcher:** The header role/tenant selector demonstrates backend RBAC and multi-tenant isolation policies (`GOV-SEC-01`) without requiring external SSO authentication during portfolio evaluation.
