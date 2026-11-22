from functools import lru_cache
from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models
from app.core.config import get_settings

settings = get_settings()

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Menginisialisasi QdrantClient (Cloud atau fallback in-memory jika URL kosong)."""
    url = settings.qdrant_url.strip()
    api_key = settings.qdrant_api_key.strip()
    if url and "isi-cluster-id" not in url:
        return QdrantClient(url=url, api_key=api_key or None, timeout=30)
    return QdrantClient(":memory:")


@lru_cache(maxsize=1)
def get_dense_embedder() -> TextEmbedding:
    """Memuat model ONNX FastEmbed dense 384-dimensi sekali saja."""
    return TextEmbedding(model_name=settings.embedding_model_name)


@lru_cache(maxsize=1)
def get_sparse_embedder() -> SparseTextEmbedding:
    """Memuat model ONNX FastEmbed BM25 sparse sekali saja."""
    return SparseTextEmbedding(model_name=settings.sparse_model_name)


def embed_dense_texts(texts: list[str]) -> list[list[float]]:
    """Menghasilkan dense embeddings 384 dimensi."""
    embedder = get_dense_embedder()
    return [vec.tolist() for vec in embedder.embed(texts)]


def embed_sparse_texts(texts: list[str]) -> list[models.SparseVector]:
    """Menghasilkan sparse BM25 vectors untuk Hybrid RRF search."""
    embedder = get_sparse_embedder()
    sparse_vectors = []
    for item in embedder.embed(texts):
        sparse_vectors.append(
            models.SparseVector(
                indices=item.indices.tolist(),
                values=item.values.tolist(),
            )
        )
    return sparse_vectors


def init_qdrant_collections() -> dict[str, str]:
    """Membuat koleksi NexusCore-Docs dan NexusCore-Cache beserta payload indexes."""
    client = get_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}
    status = {}

    # 1. Koleksi Dokumen Korporat (Hybrid Dense + BM25 Sparse)
    docs_col = settings.qdrant_docs_collection
    if docs_col not in existing:
        client.create_collection(
            collection_name=docs_col,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=settings.embedding_dimension,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                )
            },
        )
        status[docs_col] = "CREATED"
    else:
        status[docs_col] = "EXISTS"

    # Payload indexes wajib agar filtering multi-tenant di Qdrant Cloud berjalan cepat & valid
    for field_name in ("tenant_id", "doc_id", "doc_type"):
        client.create_payload_index(
            collection_name=docs_col,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    # 2. Koleksi Semantic Cache (Dense Cosine Similarity + RBAC Filter)
    cache_col = settings.qdrant_cache_collection
    if cache_col not in existing:
        client.create_collection(
            collection_name=cache_col,
            vectors_config=models.VectorParams(
                size=settings.embedding_dimension,
                distance=models.Distance.COSINE,
            ),
        )
        status[cache_col] = "CREATED"
    else:
        status[cache_col] = "EXISTS"

    for field_name in ("tenant_id", "user_role"):
        client.create_payload_index(
            collection_name=cache_col,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    return status
