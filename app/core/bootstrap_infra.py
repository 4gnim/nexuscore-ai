from sqlalchemy import inspect
from app.core.config import get_settings
from app.core.database import check_db_connection, engine, init_db
from app.core.semantic_cache import (
    invalidate_tenant_cache,
    lookup_semantic_cache,
    store_semantic_cache,
)
from app.core.vector_store import (
    embed_dense_texts,
    embed_sparse_texts,
    init_qdrant_collections,
)

settings = get_settings()


def bootstrap_all() -> None:
    print("=== Fase 2: Verifikasi Database & Tri-Store Infrastructure ===")

    # 1. PostgreSQL / Relational & Graph Tables
    db_ok = check_db_connection()
    print(f"[1/4] Koneksi Database        : {'OK' if db_ok else 'GAGAL'}")
    init_db()
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    print(f"[2/4] Tabel Terdaftar ({len(tables)})   : {', '.join(tables)}")

    # 2. Qdrant Cloud Collections & Payload Indexes
    col_status = init_qdrant_collections()
    print(f"[3/4] Koleksi Qdrant Cloud    : {col_status}")

    # 3. FastEmbed ONNX (Dense 384-dim + BM25 Sparse) & Semantic Cache Round-Trip
    sample_query = "Uji koneksi tri-store dan analisis risiko pelabuhan Kaohsiung"
    dense_vec = embed_dense_texts([sample_query])[0]
    sparse_vec = embed_sparse_texts([sample_query])[0]

    store_semantic_cache(
        query_text=sample_query,
        response_payload={"status": "verified", "risk_level": "HIGH"},
        tenant_id=settings.default_tenant_id,
        user_role="Analyst",
    )
    hit = lookup_semantic_cache(
        query_text=sample_query,
        tenant_id=settings.default_tenant_id,
        user_role="Analyst",
    )
    # Pastikan isolasi RBAC: role Viewer tidak boleh mendapatkan cache milik Analyst
    rbac_isolated = (
        lookup_semantic_cache(
            query_text=sample_query,
            tenant_id=settings.default_tenant_id,
            user_role="Viewer",
        )
        is None
    )
    invalidate_tenant_cache(settings.default_tenant_id)

    print(
        f"[4/4] FastEmbed & Cache Check : DenseDim={len(dense_vec)}, "
        f"SparseNonZero={len(sparse_vec.indices)}, "
        f"CacheHit={bool(hit)}, RBACIsolated={rbac_isolated}"
    )
    print("=== Fase 2 Selesai & Terverifikasi ===")


if __name__ == "__main__":
    bootstrap_all()
