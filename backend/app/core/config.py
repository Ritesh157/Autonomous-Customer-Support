"""Process settings (F14). Read once via ``get_settings()``; restart after .env changes."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_URL_PASSWORD = re.compile(r"(://[^:/@\s]+:)([^@/\s]+)(@)")
_REDACTED = "***"


def redact_url(url: str) -> str:
    """Hide the password part of a ``scheme://user:pass@host`` URL."""
    return _URL_PASSWORD.sub(rf"\1{_REDACTED}\3", url)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # App
    demo_mode: bool = True
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: SecretStr = SecretStr("dev-only-change-me")
    supabase_jwt_secret: SecretStr = SecretStr("")

    # Storage
    database_url: str = "sqlite+aiosqlite:///./data/support.db"
    checkpoint_db_path: str = "./data/checkpoints.db"
    redis_url: str = ""
    use_fake_redis: bool = False

    # LLM / embeddings
    llm_provider: str = "fake"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    embedding_provider: str = "fake"
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=384, gt=0)

    # Vector store
    vector_store: str = "memory"
    qdrant_url: str = ""
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_collection: str = "clouddesk_knowledge"

    # Policy / limits
    approval_required_for_refunds: bool = True
    max_refund_without_approval: float = Field(default=0, ge=0)
    tool_timeout_seconds: float = Field(default=30, gt=0)
    rate_limit_per_minute: int = Field(default=120, gt=0)
    sample_data_dir: str = "sample_data"

    # Observability
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr = SecretStr("")
    langchain_project: str = "clouddesk-support"

    @field_validator("llm_provider", "embedding_provider", "vector_store", mode="before")
    @classmethod
    def _lower(cls, v: Any) -> Any:
        return v.strip().lower() if isinstance(v, str) else v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_jwt_secret(self) -> str:
        """Supabase JWT secret when set, otherwise the local demo secret."""
        return self.supabase_jwt_secret.get_secret_value() or self.jwt_secret.get_secret_value()

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Redacted dump: secrets masked, URL passwords hidden. Attributes stay readable."""
        data = super().model_dump(**kwargs)
        for name, value in data.items():
            if isinstance(value, SecretStr):
                data[name] = _REDACTED if value.get_secret_value() else ""
            elif isinstance(value, str) and name.endswith("_url"):
                data[name] = redact_url(value)
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
