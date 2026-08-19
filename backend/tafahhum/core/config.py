"""Runtime configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from tafahhum.core.enums import Language


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TAFAHHUM_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- database -----------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5544
    postgres_db: str = "tafahhum"
    postgres_user: str = "tafahhum"
    postgres_password: str = "tafahhum_dev"
    pool_min_size: int = 1
    pool_max_size: int = 10

    # --- language -----------------------------------------------------------
    #: Retrieval always happens in this language, regardless of the user's choice.
    pivot_language: Language = Language.AR
    default_user_language: Language = Language.EN

    # --- retrieval ----------------------------------------------------------
    #: BGE-M3 produces 1024-dim vectors and handles Arabic well. Changing this
    #: requires a migration, since the column type carries the dimension.
    embedding_dimensions: int = 1024
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    sparse_candidate_limit: int = 100
    dense_candidate_limit: int = 100
    rerank_limit: int = 40
    evidence_limit: int = 12

    #: Reciprocal-rank-fusion constant. 60 is the value from the original RRF
    #: paper and is not tuned here; it is stable across very different rankers.
    rrf_k: int = 60

    # --- integrity ----------------------------------------------------------
    #: When true, retrieval reads only `published_passage`. Turning this off is a
    #: corpus-maintenance affordance and must never be done on a user-facing path.
    published_only: bool = True

    environment: str = Field(default="development")

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
