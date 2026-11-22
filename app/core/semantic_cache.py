import json
import uuid
from datetime import datetime, timezone
from typing import Any
from qdrant_client import models
from app.core.config import get_settings
from app.core.vector_store import embed_dense_texts, get_qdrant_client

settings = get_settings()


def _make_cache_point_id(tenant_id: str, user_role: str, query_text: str) -> str:
    raw_key = f"{tenant_id}::{user_role}::{query_text.strip().lower()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_key))


def lookup_semantic_cache(
    query_text: str,
    tenant_id: str,
    user_role: str,
    threshold: float | None = None,
) -> dict[str, Any] | None:
    """Mencari jawaban tersimpan di Qdrant NexusCore-Cache dengan filter tenant_id & user_role."""
    client = get_qdrant_client()
    min_score = (
        threshold if threshold is not None else settings.semantic_cache_threshold
    )
    query_vec = embed_dense_texts([query_text])[0]

    hits = client.query_points(
        collection_name=settings.qdrant_cache_collection,
        query=query_vec,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
                models.FieldCondition(
                    key="user_role",
                    match=models.MatchValue(value=user_role),
                ),
            ]
        ),
        limit=1,
        score_threshold=min_score,
        with_payload=True,
    ).points

    if not hits:
        return None

    top_hit = hits[0]
    payload = top_hit.payload or {}
    cached_json = payload.get("response_json")
    if not cached_json:
        return None

    result = json.loads(cached_json)
    result["_cache_hit"] = True
    result["_cache_score"] = round(float(top_hit.score), 4)
    result["_cached_query"] = payload.get("query_text", "")
    return result


def store_semantic_cache(
    query_text: str,
    response_payload: dict[str, Any],
    tenant_id: str,
    user_role: str,
) -> str:
    """Menyimpan hasil akhir ke Qdrant NexusCore-Cache."""
    client = get_qdrant_client()
    point_id = _make_cache_point_id(tenant_id, user_role, query_text)
    vec = embed_dense_texts([query_text])[0]

    clean_payload = {k: v for k, v in response_payload.items() if not k.startswith("_")}
    point = models.PointStruct(
        id=point_id,
        vector=vec,
        payload={
            "tenant_id": tenant_id,
            "user_role": user_role,
            "query_text": query_text.strip(),
            "response_json": json.dumps(clean_payload, ensure_ascii=False),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    client.upsert(
        collection_name=settings.qdrant_cache_collection,
        points=[point],
        wait=True,
    )
    return point_id


def invalidate_tenant_cache(tenant_id: str) -> None:
    """Menghapus entri cache untuk tenant tertentu saat data/dokumen diperbarui."""
    client = get_qdrant_client()
    client.delete(
        collection_name=settings.qdrant_cache_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="tenant_id",
                        match=models.MatchValue(value=tenant_id),
                    )
                ]
            )
        ),
        wait=True,
    )
