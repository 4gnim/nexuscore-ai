import json
from functools import lru_cache
from typing import Any
from app.core.config import get_settings
from app.rag.graph_engine import SupplyChainKnowledgeGraph
from app.rag.indexer import index_corporate_documents, search_hybrid_qdrant

settings = get_settings()


@lru_cache(maxsize=4)
def get_knowledge_graph(tenant_id: str) -> SupplyChainKnowledgeGraph:
    return SupplyChainKnowledgeGraph(tenant_id=tenant_id)


def hybrid_graphrag_retrieve(
    query: str,
    tenant_id: str | None = None,
    top_k_docs: int = 5,
    max_hops: int = 3,
) -> dict[str, Any]:
    """Menggabungkan Qdrant Hybrid Search (Dense+BM25) dan NetworkX Multi-Hop Traversal via Cross-Modal RRF."""
    target_tenant = tenant_id or settings.default_tenant_id
    kg = get_knowledge_graph(target_tenant)

    # 1. Jalur Vector + Lexical (Qdrant Cloud RRF)
    qdrant_hits = search_hybrid_qdrant(
        query=query, tenant_id=target_tenant, top_k=top_k_docs
    )

    # 2. Jalur Symbolic Multi-Hop Graph (NetworkX)
    seed_ids = kg.extract_seed_entities(query)
    subgraph = kg.traverse_multi_hop(
        seed_entity_ids=seed_ids, max_hops=max_hops, max_triples=30
    )

    # 3. Cross-Modal Reciprocal Rank Fusion (RRF) antara skor dokumen Qdrant & frekuensi bukti subgraf
    k_rrf = 60.0
    doc_scores: dict[str, float] = {}
    doc_meta: dict[str, dict[str, Any]] = {}
    doc_graph_quotes: dict[str, list[str]] = {}

    for hit in qdrant_hits:
        did = hit["doc_id"]
        doc_scores[did] = doc_scores.get(did, 0.0) + (1.0 / (k_rrf + hit["rank"]))
        doc_meta[did] = hit

    # Hitung dukungan bukti dari relasi graf yang terhubung ke dokumen sumber
    doc_triple_counts: dict[str, int] = {}
    for triple in subgraph["triples"]:
        did = triple["source_doc_id"]
        if did.startswith("DOC-"):
            doc_triple_counts[did] = doc_triple_counts.get(did, 0) + 1
            doc_graph_quotes.setdefault(did, []).append(
                f"({triple['subject_name']})-[{triple['predicate']}]->({triple['object_name']}): \"{triple['evidence_quote']}\""
            )

    ranked_graph_docs = sorted(
        doc_triple_counts.items(), key=lambda x: x[1], reverse=True
    )
    for g_rank, (did, _) in enumerate(ranked_graph_docs, start=1):
        doc_scores[did] = doc_scores.get(did, 0.0) + (1.0 / (k_rrf + g_rank))

    # Lengkapi metadata bila ada dokumen yang muncul kuat di graf namun belum masuk top_k_docs Qdrant
    if any(did not in doc_meta for did in doc_scores):
        with (settings.docs_data_dir / "corp_docs.json").open(
            "r", encoding="utf-8"
        ) as f:
            all_docs = {d["doc_id"]: d for d in json.load(f)}
        for did in doc_scores:
            if did not in doc_meta and did in all_docs:
                d = all_docs[did]
                doc_meta[did] = {
                    "doc_id": did,
                    "title": d["title"],
                    "doc_type": d["doc_type"],
                    "effective_date": d.get("effective_date", ""),
                    "content": d["content"],
                }

    fused_documents: list[dict[str, Any]] = []
    for did, score in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[
        :top_k_docs
    ]:
        meta = doc_meta[did]
        fused_documents.append(
            {
                "doc_id": did,
                "title": meta["title"],
                "doc_type": meta["doc_type"],
                "effective_date": meta.get("effective_date", ""),
                "fused_rrf_score": round(score, 5),
                "content": meta["content"],
                "supporting_graph_triples": doc_graph_quotes.get(did, [])[:4],
            }
        )

    formatted_paths = [
        f"[Hop {t['hop']}] {t['subject_name']} ({t['subject_code'] or 'N/A'}) "
        f"--[{t['predicate']}]--> {t['object_name']} ({t['object_code'] or 'N/A'}) "
        f"[Sumber: {t['source_doc_id']}]"
        for t in subgraph["triples"][:20]
    ]

    return {
        "query": query,
        "tenant_id": target_tenant,
        "seed_entities": subgraph["seed_entities"],
        "shortest_paths": subgraph["shortest_paths"],
        "reasoning_paths": formatted_paths,
        "fused_documents": fused_documents,
        "citations": [
            {
                "doc_id": d["doc_id"],
                "title": d["title"],
                "doc_type": d["doc_type"],
                "fused_rrf_score": d["fused_rrf_score"],
            }
            for d in fused_documents
        ],
        "top_systemic_bottlenecks": kg.get_top_central_entities(top_n=5),
        "cytoscape": subgraph["cytoscape"],
    }


if __name__ == "__main__":
    idx_res = index_corporate_documents()
    print("=== [1/2] Qdrant Cloud Document Indexing Selesai ===")
    print(json.dumps(idx_res, indent=2, ensure_ascii=False))

    test_query = (
        "Jika Port of Kaohsiung mengalami kemacetan parah > 85, produk ApexGlobal mana saja yang "
        "terdampak, pemasok cadangan mana yang bebas tarif TAR-2026-88, dan apa syarat persetujuan HITL?"
    )
    rag_res = hybrid_graphrag_retrieve(test_query, top_k_docs=5, max_hops=3)
    print("\n=== [2/2] Hybrid GraphRAG Multi-Hop Retrieval Verification ===")
    print(
        json.dumps(
            {
                "seed_entities": rag_res["seed_entities"],
                "shortest_paths": rag_res["shortest_paths"],
                "top_systemic_bottlenecks": rag_res["top_systemic_bottlenecks"],
                "citations": rag_res["citations"],
                "sample_reasoning_paths": rag_res["reasoning_paths"][:8],
                "cytoscape_counts": {
                    "nodes": len(rag_res["cytoscape"]["nodes"]),
                    "edges": len(rag_res["cytoscape"]["edges"]),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
