import json
import uuid
from typing import Any
from qdrant_client import models
from app.core.config import get_settings
from app.core.vector_store import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    embed_dense_texts,
    embed_sparse_texts,
    get_qdrant_client,
    init_qdrant_collections,
)

settings = get_settings()


def _doc_point_id(tenant_id: str, doc_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant_id}::doc::{doc_id}"))


def index_corporate_documents(tenant_id: str | None = None) -> dict[str, Any]:
    """Mengindeks seluruh dokumen korporat ke Qdrant Cloud (Dense + BM25 Sparse)."""
    init_qdrant_collections()
    client = get_qdrant_client()
    target_tenant = tenant_id or settings.default_tenant_id

    docs_path = settings.docs_data_dir / "corp_docs.json"
    with docs_path.open("r", encoding="utf-8") as f:
        corp_docs = json.load(f)

    filtered_docs = [
        d for d in corp_docs if d.get("tenant_id", target_tenant) == target_tenant
    ]
    if not filtered_docs:
        return {"indexed_count": 0, "collection": settings.qdrant_docs_collection}

    texts_to_embed = [
        f"[{doc['doc_id']}] {doc['title']} ({doc['doc_type']})\n{doc['content']}"
        for doc in filtered_docs
    ]

    dense_vectors = embed_dense_texts(texts_to_embed)
    sparse_vectors = embed_sparse_texts(texts_to_embed)

    points: list[models.PointStruct] = []
    for doc, dense_vec, sparse_vec in zip(filtered_docs, dense_vectors, sparse_vectors):
        point_id = _doc_point_id(target_tenant, doc["doc_id"])
        points.append(
            models.PointStruct(
                id=point_id,
                vector={
                    DENSE_VECTOR_NAME: dense_vec,
                    SPARSE_VECTOR_NAME: sparse_vec,
                },
                payload={
                    "tenant_id": target_tenant,
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "doc_type": doc["doc_type"],
                    "effective_date": doc.get("effective_date", ""),
                    "content": doc["content"],
                },
            )
        )

    client.upsert(
        collection_name=settings.qdrant_docs_collection,
        points=points,
        wait=True,
    )

    return {
        "collection": settings.qdrant_docs_collection,
        "tenant_id": target_tenant,
        "indexed_documents": len(points),
        "doc_ids": [d["doc_id"] for d in filtered_docs],
    }


def search_hybrid_qdrant(
    query: str,
    tenant_id: str | None = None,
    top_k: int = 5,
    doc_type_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Menjalankan Hybrid Search (Dense Cosine + BM25 Sparse RRF) di Qdrant Cloud."""
    client = get_qdrant_client()
    target_tenant = tenant_id or settings.default_tenant_id

    must_conditions: list[models.FieldCondition] = [
        models.FieldCondition(
            key="tenant_id",
            match=models.MatchValue(value=target_tenant),
        )
    ]
    if doc_type_filter:
        must_conditions.append(
            models.FieldCondition(
                key="doc_type",
                match=models.MatchValue(value=doc_type_filter),
            )
        )

    tenant_filter = models.Filter(must=must_conditions)
    dense_vec = embed_dense_texts([query])[0]
    sparse_vec = embed_sparse_texts([query])[0]

    response = client.query_points(
        collection_name=settings.qdrant_docs_collection,
        prefetch=[
            models.Prefetch(
                query=dense_vec,
                using=DENSE_VECTOR_NAME,
                filter=tenant_filter,
                limit=max(top_k * 2, 8),
            ),
            models.Prefetch(
                query=sparse_vec,
                using=SPARSE_VECTOR_NAME,
                filter=tenant_filter,
                limit=max(top_k * 2, 8),
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )

    results: list[dict[str, Any]] = []
    for rank, point in enumerate(response.points, start=1):
        payload = point.payload or {}
        results.append(
            {
                "rank": rank,
                "rrf_score": round(float(point.score), 5),
                "doc_id": payload.get("doc_id", ""),
                "title": payload.get("title", ""),
                "doc_type": payload.get("doc_type", ""),
                "effective_date": payload.get("effective_date", ""),
                "content": payload.get("content", ""),
            }
        )
    return results
