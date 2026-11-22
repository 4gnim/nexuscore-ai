# NexusCore AI — Enterprise Supply Chain Intelligence & Resilience Platform

## 1. Ringkasan Eksekutif & Studi Kasus Bisnis

**NexusCore AI** adalah platform kecerdasan rantai pasok dan ketahanan operasional (*Supply Chain Resilience*) yang dirancang untuk studi kasus **ApexGlobal Manufacturing Corp**, perusahaan manufaktur elektronik dan perangkat keras industri internasional.

### Profil Operasional ApexGlobal Manufacturing Corp
- **Jaringan Pemasok Global:** 8 pemasok strategis (Tier-1 & Tier-2) lintas negara (Taiwan, Korea Selatan, Jepang, Jerman, Vietnam, Malaysia, Amerika Serikat, dan Indonesia).
- **Komponen Kritis:** 10 komponen berteknologi tinggi (semikonduktor 5nm, sel baterai LiFePO4, SiC MOSFET, MEMS gyroscope, substrat RF PCB, dll.).
- **Portofolio Produk:** 6 lini produk utama pada divisi *Edge Computing*, *Clean Energy Grid*, dan *Industrial Robotics*.
- **Jaringan Gudang:** 3 pusat distribusi dan perakitan (`WH-ID` sebagai hub perakitan utama di Indonesia, `WH-SG` di Singapura, dan `WH-DE` di Jerman).
- **Batasan Keuangan & Regulasi:**
  - Terikat pada perjanjian kredit sindikasi (*Financial Debt Covenant* **`COV-FIN-01`**) yang mewajibkan **Consolidated Gross Margin minimal 28,0%** setiap kuartal.
  - Terikat pada prosedur darurat **`SOP-SC-04`** yang mewajibkan persetujuan **Human-in-the-Loop (HITL)** oleh peran `SupplyChainDirector` apabila total biaya paket mitigasi melebihi **USD 50.000**.

---

## 2. Arsitektur Sistem End-to-End (6 Lapisan)

Diagram berikut menggambarkan alur data, inferensi ML, penalaran graf hibrida, simulasi kuantitatif, hingga orkestrasi multi-agen pada **NexusCore AI**:

    +-----------------------------------------------------------------------------------+
    |                        LAYER 6: EXECUTIVE WAR ROOM & API                          |
    |  FastAPI Async SSE Streaming | Cytoscape.js Graph | Chart.js Sim | HITL Approval  |
    +-----------------------------------------------------------------------------------+
                                             ^
                                             |
    +-----------------------------------------------------------------------------------+
    |                 LAYER 5: ENTERPRISE SECURITY & GOVERNANCE GUARD                   |
    |  RBAC (Viewer/Analyst/Director) | Tenant Isolation | Prompt Injection | Audit Log |
    +-----------------------------------------------------------------------------------+
                                             ^
                                             |
    +-----------------------------------------------------------------------------------+
    |               LAYER 4: HIERARCHICAL MULTI-AGENT SWARM (LANGGRAPH)                 |
    |  Meta-Planner ---> [Graph Worker || ML/SQL Worker || Compliance Worker]           |
    |                                         |                                         |
    |                             Adversarial Red-Team Critic                           |
    |                                         |                                         |
    |                               Executive Synthesizer                               |
    +-----------------------------------------------------------------------------------+
             ^                                ^                                ^
             |                                |                                |
    +--------------------+   +---------------------------------+   +--------------------+
    | LAYER 3A: HYBRID   |   | LAYER 3B: DETERMINISTIC QUANT   |   | LAYER 2: PREDICTIVE|
    | GRAPHRAG ENGINE    |   | SIMULATION ENGINE (FASTMCP)     |   | ML & MLOPS         |
    | NetworkX Multi-Hop |   | Monte Carlo (1,000 runs)        |   | XGBoost Delay &    |
    | + Qdrant RRF       |   | Covenant Sensitivity & Optimizer|   | Stockout + MLflow  |
    +--------------------+   +---------------------------------+   +--------------------+
             ^                                ^                                ^
             +--------------------------------+--------------------------------+
                                              |
    +-----------------------------------------------------------------------------------+
    |                LAYER 1: ENTERPRISE DATA PLATFORM & TRI-STORE                      |
    |  Raw CSV/JSON -> Data Quality Gate -> DLQ Isolation -> Cleaned/Curated Parquet    |
    |  PostgreSQL (Relational + KG + Audit) | Qdrant Cloud (Docs + Semantic Cache)      |
    +-----------------------------------------------------------------------------------+

### Penjelasan Tiap Lapisan
1. **Layer 1 — Enterprise Data Platform & Tri-Store:**
   - Mengelola ingesti data batch/streaming melalui arsitektur *Medallion* (*Raw $\rightarrow$ Cleaned $\rightarrow$ Curated* dalam format Parquet + PostgreSQL).
   - Validasi kualitas data otomatis mengisolasi anomali ke *Dead-Letter Queue* (`data/dlq/`).
   - **Tri-Store Persistence:** Supabase PostgreSQL (data relasional, Knowledge Graph, audit log), Qdrant Cloud (koleksi dokumen & semantic cache), dan local/cloud Parquet analytics store.
2. **Layer 2 — Predictive Machine Learning & MLOps:**
   - Pipeline *feature engineering* menghasilkan model **XGBoost** untuk memprediksi probabilitas keterlambatan pemasok (*Supplier Delay Risk*) dan proyeksi kehabisan stok (*Stockout Risk*).
   - Seluruh eksperimen, metrik (PR-AUC, F1, MAE), dan artefak model dicatat melalui **MLflow**.
3. **Layer 3A — Knowledge Graph & Hybrid GraphRAG Engine:**
   - Ekstraksi entitas dan relasi `(Subject)-[RELATION]->(Object)` dari dokumen korporat ke PostgreSQL (`kg_entities`, `kg_relations`) dengan *entity resolution*.
   - Menggabungkan traversal multi-hop, *shortest path*, dan *PageRank* via **NetworkX** dengan pencarian vektor hibrida **Qdrant (Dense + BM25 RRF)** serta *citation provenance*.
4. **Layer 3B — Deterministic Quantitative Simulation Engine (FastMCP):**
   - Menjalankan simulasi terverifikasi tanpa `exec()` Python bebas oleh LLM (mematuhi standar keamanan OWASP GenAI): simulasi **Monte Carlo 1.000 skenario**, analisis sensitivitas batas margin kovenan `COV-FIN-01`, dan optimasi pemasok cadangan.
5. **Layer 4 — Hierarchical Multi-Agent Swarm (LangGraph):**
   - `Meta-Planner Agent` memecah investigasi menjadi sub-tugas paralel menggunakan LangGraph `Send` API (`Graph Investigator Worker`, `ML & SQL Data Scientist Worker`, dan `Risk & Compliance Auditor Worker`).
   - `Adversarial Red-Team Critic` memverifikasi konsistensi angka SQL/ML terhadap bukti dokumen/graf dan memicu revisi apabila ditemukan kontradiksi.
6. **Layer 5 & 6 — Enterprise Governance & Executive War Room:**
   - Penegakan RBAC (`Viewer`, `Analyst`, `SupplyChainDirector`), isolasi `tenant_id`, deteksi *prompt injection*, antrean persetujuan HITL (> USD 50.000), *append-only audit trail*, serta antarmuka streaming SSE dengan visualisasi **Cytoscape.js** dan **Chart.js**.

---

## 3. Entity-Relationship Diagram (ERD)

Seluruh tabel inti menerapkan isolasi baris multi-tenant melalui kolom `tenant_id`:

    [suppliers] 1 ----< * [components] (via primary_supplier_id & backup_supplier_id)
         |                     |
         |                     +----< * [bom] * >---- 1 [products]
         |                     |
         |                     +----< * [inventory]
         |                     |
         +----------< * [shipments_history] * >---- 1 [components]

    [kg_entities] 1 ----< * [kg_relations] (via subject_id & object_id)

    [audit_logs] (append-only governance log per tenant_id)
    [hitl_approvals] (approval queue untuk paket mitigasi > USD 50,000)

---

## 4. Data Dictionary (Kamus Data Enterprise)

### 4.1 Tabel `suppliers` (Master Pemasok)
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `supplier_id` | `VARCHAR(16)` (PK) | Kode unik pemasok (contoh: `SUP-001`) |
| `tenant_id` | `VARCHAR(32)` | Identitas tenant perusahaan (`TENANT-APEX-GLOBAL`) |
| `supplier_name` | `VARCHAR(128)` | Nama resmi entitas pemasok |
| `country` | `VARCHAR(64)` | Negara lokasi pabrik utama |
| `port_hub` | `VARCHAR(64)` | Pelabuhan ekspor utama pemasok |
| `tier` | `VARCHAR(16)` | Klasifikasi rantai pasok (`Tier-1` / `Tier-2`) |
| `financial_health_score` | `FLOAT` | Skor kesehatan finansial (0–100) |
| `geopolitical_risk_index` | `FLOAT` | Indeks risiko geopolitik & jalur maritim (0–100) |
| `esg_score` | `FLOAT` | Skor kepatuhan ESG & mineral bertanggung jawab (0–100) |
| `contracted_lead_time_days` | `INTEGER` | Waktu tunggu pengiriman standar sesuai kontrak (hari) |
| `unit_cost_multiplier` | `FLOAT` | Faktor pengali biaya terhadap biaya standar komponen |
| `monthly_capacity_units` | `INTEGER` | Kapasitas produksi bulanan maksimum (unit) |
| `is_approved_backup` | `BOOLEAN` | Status kualifikasi PPAP sebagai pemasok cadangan |

### 4.2 Tabel `components` (Master Komponen Kritis)
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `component_id` | `VARCHAR(16)` (PK) | Kode unik komponen (contoh: `CMP-001`) |
| `tenant_id` | `VARCHAR(32)` | Identitas tenant perusahaan |
| `component_name` | `VARCHAR(128)` | Nama teknis komponen |
| `category` | `VARCHAR(64)` | Kategori komponen (`Semiconductors`, `Energy Storage`, dll.) |
| `primary_supplier_id` | `VARCHAR(16)` (FK) | Referensi ke `suppliers.supplier_id` pemasok utama |
| `backup_supplier_id` | `VARCHAR(16)` (FK) | Referensi ke `suppliers.supplier_id` pemasok cadangan |
| `criticality` | `VARCHAR(16)` | Tingkat kekritisan (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) |
| `standard_unit_cost_usd` | `FLOAT` | Biaya standar per unit dalam USD |
| `hs_code` | `VARCHAR(16)` | Kode klasifikasi tarif kepabeanan internasional |
| `base_tariff_pct` | `FLOAT` | Tarif bea masuk dasar (%) |

### 4.3 Tabel `products` & `bom` (Produk Jadi & Bill of Materials)
| Tabel | Kolom Utama | Tipe Data | Keterangan |
| :--- | :--- | :--- | :--- |
| `products` | `product_id` (PK) | `VARCHAR(16)` | Kode produk jadi (`PRD-001` s.d. `PRD-006`) |
| `products` | `selling_price_usd` | `FLOAT` | Harga jual rata-rata per unit (USD) |
| `products` | `standard_cogs_usd` | `FLOAT` | Harga pokok produksi standar per unit (USD) |
| `products` | `gross_margin_pct` | `FLOAT` | Margin kotor baseline produk (%) |
| `products` | `monthly_demand_units` | `INTEGER` | Permintaan pasar bulanan rata-rata (unit) |
| `bom` | `bom_id` (PK) | `VARCHAR(16)` | Kode baris struktur BOM |
| `bom` | `product_id` / `component_id` | `VARCHAR(16)` (FK) | Relasi komposisi komponen ke produk |
| `bom` | `qty_per_unit` | `INTEGER` | Jumlah unit komponen per 1 unit produk jadi |
| `bom` | `is_single_source_risk` | `BOOLEAN` | Penanda ketergantungan tinggi pada satu pemasok |

### 4.4 Tabel `inventory` & `shipments_history`
| Tabel | Kolom Utama | Tipe Data | Keterangan |
| :--- | :--- | :--- | :--- |
| `inventory` | `inventory_id` (PK) | `VARCHAR(16)` | Kode catatan stok per gudang (`WH-ID`, `WH-SG`, `WH-DE`) |
| `inventory` | `on_hand_qty` / `reserved_qty` | `INTEGER` | Stok fisik tersedia dan stok yang sudah dialokasikan |
| `inventory` | `daily_burn_rate` | `FLOAT` | Konsumsi rata-rata harian lini produksi (unit/hari) |
| `shipments_history` | `shipment_id` (PK) | `VARCHAR(24)` | Kode unik transaksi pengiriman |
| `shipments_history` | `port_congestion_index` | `FLOAT` | Indeks kemacetan pelabuhan asal saat pengiriman (0–100) |
| `shipments_history` | `weather_severity_index` | `FLOAT` | Indeks cuaca ekstrem jalur maritim/udara (0–100) |
| `shipments_history` | `supplier_health_at_order` | `FLOAT` | Skor kesehatan pemasok saat PO diterbitkan |
| `shipments_history` | `delay_days` / `is_delayed` | `INTEGER` | Selisih hari keterlambatan & label target klasifikasi ML |

### 4.5 Tabel Knowledge Graph & Governance (`kg_entities`, `kg_relations`, `audit_logs`, `hitl_approvals`)
- **`kg_entities`:** `entity_id` (PK), `tenant_id`, `entity_name`, `entity_type`, `source_doc_id`, `metadata_json`.
- **`kg_relations`:** `relation_id` (PK), `tenant_id`, `subject_id` (FK), `predicate`, `object_id` (FK), `confidence`, `evidence_quote`, `source_doc_id`.
- **`audit_logs`:** `log_id` (PK), `tenant_id`, `user_id`, `user_role`, `action_type`, `query_text`, `security_status`, `model_used`, `latency_ms`, `created_at`.
- **`hitl_approvals`:** `approval_id` (PK), `tenant_id`, `session_id`, `requested_by`, `mitigation_summary`, `estimated_cost_usd`, `covenant_impact_pct`, `status` (`PENDING`, `APPROVED`, `REJECTED`), `reviewed_by`, `reviewed_at`.

---

## 5. Aturan Bisnis & Batas Tata Kelola (Governance Guardrails)

1. **Kovenan Keuangan `COV-FIN-01`:** Margin kotor konsolidasi tidak boleh turun di bawah **$28,0\%$**. Setiap simulasi mitigasi harus menghitung dampak biaya tambahan terhadap margin produk dan margin konsolidasi.
2. **Ambang Persetujuan HITL (`SOP-SC-04`):** Paket mitigasi dengan total biaya tambahan $> \text{USD } 50.000$ wajib berstatus `PENDING_HITL_APPROVAL` dan hanya dapat disetujui oleh pengguna dengan peran `SupplyChainDirector`.
3. **Tarif Kepabeanan (`TAR-2026-88`):** Pengiriman semikonduktor (`8542.31`) dan RF PCB (`8534.00`) melalui pelabuhan non-FTA dikenakan bea masuk tambahan $+18,0\%$, kecuali dialihkan ke pemasok tersertifikasi FTA (`SUP-002` Korea Selatan atau `SUP-006` Malaysia).
4. **Kepatuhan ESG (`ESG-2026-03`):** Pemasok dengan `esg_score < 80.0` otomatis didiskualifikasi dari rekomendasi optimasi rantai pasok.

---

## 6. Spesifikasi Model AI & Infrastruktur Cloud

- **LLM Primary (Reasoning & Agents):** `openai/gpt-oss-120b` (Groq)
- **LLM Fast (Extraction & Workers):** `qwen/qwen3.8-27b` (Groq)
- **LLM Fallback Cascade:** `gemini-3.6-flash` $\rightarrow$ `gemini-3.5-flash-lite` $\rightarrow$ `gemini-3.1-flash-lite`
- **Dense & Sparse Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim ONNX) + `Qdrant/bm25` (Reciprocal Rank Fusion)
- **Vector Store:** Qdrant Cloud (`NexusCore-Docs` & `NexusCore-Cache`)
- **Database Relasional & Graf:** Supabase PostgreSQL (Session Pooler IPv4)
- **Observability:** Langfuse Cloud (`nexuscore-ai`)

---

## 7. Dual Deployment Profile

1. **Local Enterprise Stack (`DEPLOYMENT_PROFILE=local_enterprise`):**
   - Menjalankan seluruh layanan menggunakan `docker-compose.yml` (FastAPI Backend, MLflow Tracking Server, PostgreSQL/Supabase Pooler, Qdrant Cloud, dan Executive War Room UI).
2. **Public Cloud Demo (`DEPLOYMENT_PROFILE=hf_public_demo`):**
   - Dikonfigurasi khusus untuk **Hugging Face Spaces Free Tier (2 vCPU, 16 GB RAM)** menggunakan `run_hf.py` (Gradio wrapper + FastAPI mounted routes dengan `ssr_mode=False`) agar ringan, stabil, dan dapat diakses publik.