---
title: NexusCore AI
emoji: ðŸ›¡ï¸
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# NexusCore AI â€” Enterprise Supply Chain Intelligence & Resilience Platform

**NexusCore AI** is an end-to-end enterprise supply chain risk intelligence and decision-orchestration platform that integrates **Medallion Data Engineering**, **Hybrid GraphRAG (NetworkX + Qdrant Cloud)**, **Predictive Machine Learning (XGBoost + MLflow)**, **1,000-Iteration Monte Carlo Risk Simulation**, **Parallel Multi-Agent Orchestration (LangGraph)**, and **Human-in-the-Loop (HITL) Governance** backed by a **SHA-256 hash-chained audit ledger**.

Instead of relying on an LLM to guess operational metrics or approve high-risk financial actions autonomously, NexusCore AI separates deterministic quantitative computation from generative reasoningâ€”tracing multi-hop supplier dependencies, forecasting warehouse stockouts, verifying debt covenant compliance (`COV-FIN-01`), and streaming audited executive briefs in real time.

## Key Capabilities & System Architecture

```text
[Raw Enterprise CSVs & Corporate Policy JSON]
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 1. Medallion Data Engineering & Quality Gate (app/data_eng)                              â”‚
â”‚    â€¢ Schema validation + Dead-Letter Queue (data/dlq/shipments_dlq.json)                 â”‚
â”‚    â€¢ Cleaned & Curated Parquet Marts (data/curated/inventory_risk_mart.parquet)          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
         â–¼                       â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 2. Predictive ML    â”‚ â”‚ 3. Hybrid GraphRAG Engine (app/kg & app/rag)                     â”‚
â”‚    (app/ml)         â”‚ â”‚    â€¢ NetworkX directed KG + PageRank bottleneck centrality       â”‚
â”‚    â€¢ XGBoost delay  â”‚ â”‚    â€¢ Qdrant Cloud Dense + BM25 Reciprocal Rank Fusion (RRF)      â”‚
â”‚      & stockout     â”‚ â”‚      across SOPs, tariff rules & debt covenants                  â”‚
â”‚    â€¢ MLflow registryâ”‚ â”‚    â€¢ Tenant-isolated semantic query cache (NexusCore-Cache)      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚                       â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 4. Parallel Multi-Agent Swarm (LangGraph Send API + SSE Streaming)                       â”‚
â”‚    â€¢ Meta-Planner Agent â”€â”€â–¶ Dispatches 3 specialist workers in parallel:                 â”‚
â”‚      [Graph Investigator]   [ML & SQL Data Scientist]   [Risk & Compliance Auditor]      â”‚
â”‚    â€¢ Adversarial Red-Team Critic â”€â”€â–¶ Audits numerical & policy consistency               â”‚
â”‚    â€¢ Executive Synthesizer â”€â”€â–¶ Decision brief, Cytoscape subgraph & Chart.js insights    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 5. Governance, RBAC & HITL Control Layer (app/security & app/sim)                        â”‚
â”‚    â€¢ Prompt/SQL injection guardrails & tenant scope isolation (GOV-SEC-01)               â”‚
â”‚    â€¢ 1,000-iteration Monte Carlo cost & COV-FIN-01 (28.0% margin floor) simulator        â”‚
â”‚    â€¢ Auto-escalation (> USD 50,000) to SupplyChainDirector HITL approval queue           â”‚
â”‚    â€¢ Tamper-evident SHA-256 hash-chained audit ledger (Supabase PostgreSQL / SQLite)     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
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
â”œâ”€â”€ app/
â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â”œâ”€â”€ state.py              # TypedDict state schema for LangGraph parallel swarm
â”‚   â”‚   â””â”€â”€ swarm.py              # 6-node LangGraph Send-API workflow & SSE trace emitter
â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â”œâ”€â”€ routes.py             # FastAPI endpoints, SSE streaming, simulation & HITL routes
â”‚   â”‚   â””â”€â”€ schemas.py            # Strict Pydantic request/response contracts
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”œâ”€â”€ bootstrap_infra.py    # Startup initialization & infrastructure bootstrap
â”‚   â”‚   â”œâ”€â”€ config.py             # Pydantic settings & environment configuration
â”‚   â”‚   â”œâ”€â”€ database.py           # SQLAlchemy engine & Supabase PostgreSQL / SQLite session
â”‚   â”‚   â”œâ”€â”€ llm_router.py         # Multi-provider LLM router (Gemini + Groq) & Langfuse tracing
â”‚   â”‚   â”œâ”€â”€ semantic_cache.py     # Qdrant-backed tenant-isolated semantic query cache
â”‚   â”‚   â””â”€â”€ vector_store.py       # Qdrant Cloud hybrid Dense + Sparse vector client
â”‚   â”œâ”€â”€ data_eng/
â”‚   â”‚   â”œâ”€â”€ etl_pipeline.py       # Medallion ETL pipeline (raw CSV -> cleaned -> curated Parquet)
â”‚   â”‚   â”œâ”€â”€ quality_gate.py       # Schema validation & Dead-Letter Queue (DLQ) quarantine
â”‚   â”‚   â””â”€â”€ stream_simulator.py   # Logistics telemetry & port congestion event simulator
â”‚   â”œâ”€â”€ kg/
â”‚   â”‚   â”œâ”€â”€ entity_resolver.py    # Canonical entity resolution across structured & text sources
â”‚   â”‚   â””â”€â”€ extractor.py          # Knowledge Graph triple extraction & snapshot builder
â”‚   â”œâ”€â”€ mcp/
â”‚   â”‚   â””â”€â”€ server.py             # Model Context Protocol (MCP) server for enterprise tools
â”‚   â”œâ”€â”€ ml/
â”‚   â”‚   â”œâ”€â”€ features.py           # Supply chain & lead-time feature engineering
â”‚   â”‚   â”œâ”€â”€ predictor.py          # XGBoost delay & stockout inference engine
â”‚   â”‚   â””â”€â”€ train_models.py       # Model training & MLflow artifact registration
â”‚   â”œâ”€â”€ rag/
â”‚   â”‚   â”œâ”€â”€ graph_engine.py       # NetworkX multi-hop traversal & PageRank centrality engine
â”‚   â”‚   â”œâ”€â”€ hybrid_graphrag.py    # Reciprocal Rank Fusion (Dense + BM25 + Graph context)
â”‚   â”‚   â””â”€â”€ indexer.py            # Enterprise SOP/contract chunking & Qdrant indexing
â”‚   â”œâ”€â”€ security/
â”‚   â”‚   â”œâ”€â”€ audit_hitl.py         # SHA-256 hash-chained audit ledger & HITL ticket manager
â”‚   â”‚   â”œâ”€â”€ guardrails.py         # Prompt/SQL injection detection & tenant/RBAC enforcement
â”‚   â”‚   â””â”€â”€ secured_runner.py     # Policy-wrapped execution runner
â”‚   â”œâ”€â”€ sim/
â”‚   â”‚   â”œâ”€â”€ monte_carlo.py        # 1,000-iteration stochastic cost & COV-FIN-01 simulator
â”‚   â”‚   â””â”€â”€ optimizer.py          # Multi-strategy mitigation utility optimizer
â”‚   â””â”€â”€ main.py                   # FastAPI entrypoint, lifespan setup & static frontend mount
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ cleaned/                  # Validated Parquet tables (bom, components, inventory, etc.)
â”‚   â”œâ”€â”€ curated/                  # Curated marts (inventory_risk_mart.parquet, kg_snapshot.json)
â”‚   â”œâ”€â”€ dlq/                      # Data quality reports & quarantined shipment records
â”‚   â”œâ”€â”€ documents/                # Enterprise policies, covenants & contracts (corp_docs.json)
â”‚   â”œâ”€â”€ raw/                      # Synthetic enterprise CSV source tables
â”‚   â”œâ”€â”€ generate_enterprise_data.py
â”‚   â””â”€â”€ golden_dataset.json
â”œâ”€â”€ docs/
â”‚   â””â”€â”€ ARCHITECTURE.md           # Detailed system architecture specification
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ app.js                    # SSE client, Cytoscape.js explorer, Chart.js dynamic insights
â”‚   â”œâ”€â”€ index.html                # Dual-persona Light-First Enterprise SaaS UI
â”‚   â””â”€â”€ styles.css                # Minimalist design system tokens & responsive layout
â”œâ”€â”€ models_registry/              # Trained Joblib artifacts & SQLite MLflow tracking store
â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ test_nexuscore_e2e.py     # End-to-end Pytest evaluation & regression suite
â”œâ”€â”€ .dockerignore
â”œâ”€â”€ .env.example
â”œâ”€â”€ Dockerfile                    # Hugging Face Spaces (port 7860, UID 1000) & container build
â”œâ”€â”€ README.md
â””â”€â”€ requirements.txt
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

1. Open your Space **Settings** on Hugging Face and set **Space hardware** to `CPU basic (2 vCPU Â· 16 GB RAM Â· Free)`.
2. Add your `.env` credentials (`GEMINI_API_KEY`, `GROQ_API_KEY`, `SUPABASE_DB_URL`, `QDRANT_URL`, `QDRANT_API_KEY`, etc.) under **Variables and secrets**.
3. Push this repository to the Space remote (`git push --force hf main`) to trigger the container build and launch the FastAPI server on port `7860`.

## Limitations & Scope

- **Simulated Enterprise Dataset:** All suppliers, components, shipments, contracts, and financial baselines represent simulated data for _ApexGlobal Manufacturing Corp_ designed to demonstrate end-to-end AI systems engineering.
- **Demo Session Role Switcher:** The header role/tenant selector demonstrates backend RBAC and multi-tenant isolation policies (`GOV-SEC-01`) without requiring external SSO authentication during portfolio evaluation.
