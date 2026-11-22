from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Konfigurasi terpusat NexusCore AI Enterprise Platform."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Metadata
    app_name: str = Field(default="NexusCore AI")
    app_version: str = Field(default="1.0.0")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    deployment_profile: Literal["local_enterprise", "hf_public_demo"] = Field(
        default="local_enterprise"
    )
    log_level: str = Field(default="INFO")

    # LLM Providers & Verified Model IDs
    groq_api_key: str = Field(default="")
    groq_primary_model: str = Field(default="openai/gpt-oss-120b")
    groq_fast_model: str = Field(default="qwen/qwen3.8-27b")

    gemini_api_key: str = Field(default="")
    gemini_fallback_model: str = Field(default="gemini-3.6-flash")
    gemini_lite_model_1: str = Field(default="gemini-3.5-flash-lite")
    gemini_lite_model_2: str = Field(default="gemini-3.1-flash-lite")

    # Embedding & Qdrant Cloud
    embedding_model_name: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    sparse_model_name: str = Field(default="Qdrant/bm25")
    embedding_dimension: int = Field(default=384)
    qdrant_url: str = Field(default="")
    qdrant_api_key: str = Field(default="")
    qdrant_docs_collection: str = Field(default="NexusCore-Docs")
    qdrant_cache_collection: str = Field(default="NexusCore-Cache")

    # Relational & Graph Database (Supabase PostgreSQL)
    supabase_db_url: str = Field(default="sqlite:///./nexuscore_local.db")

    # Observability (Langfuse)
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # Enterprise Governance, Risk & Security Thresholds
    default_tenant_id: str = Field(default="TENANT-APEX-GLOBAL")
    hitl_approval_threshold_usd: float = Field(default=50000.0)
    covenant_min_gross_margin_pct: float = Field(default=28.0)
    semantic_cache_threshold: float = Field(default=0.92)

    # Local Directory Paths
    data_dir: Path = Field(default=BASE_DIR / "data")
    raw_data_dir: Path = Field(default=BASE_DIR / "data" / "raw")
    cleaned_data_dir: Path = Field(default=BASE_DIR / "data" / "cleaned")
    curated_data_dir: Path = Field(default=BASE_DIR / "data" / "curated")
    dlq_data_dir: Path = Field(default=BASE_DIR / "data" / "dlq")
    docs_data_dir: Path = Field(default=BASE_DIR / "data" / "documents")
    models_registry_dir: Path = Field(default=BASE_DIR / "models_registry")

    @field_validator("supabase_db_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, value: str) -> str:
        if not value:
            return "sqlite:///./nexuscore_local.db"
        cleaned = value.strip().strip('"').strip("'")
        if cleaned.startswith("postgres://"):
            cleaned = cleaned.replace("postgres://", "postgresql+psycopg://", 1)
        elif cleaned.startswith("postgresql://") and "+psycopg" not in cleaned:
            cleaned = cleaned.replace("postgresql://", "postgresql+psycopg://", 1)
        return cleaned

    @property
    def fallback_model_cascade(self) -> list[str]:
        return [
            self.gemini_fallback_model,
            self.gemini_lite_model_1,
            self.gemini_lite_model_2,
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
