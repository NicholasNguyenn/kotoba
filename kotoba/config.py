"""Central settings, loaded from the environment (.env in development).

Every Azure identifier lives here so no module reaches for os.environ directly.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_chat_deployment: str = "gpt-5-mini"
    embedding_dimensions: int = 1536

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index: str = "kotoba-grammar"
    azure_search_semantic_enabled: bool = True

    @field_validator("azure_openai_endpoint", mode="after")
    @classmethod
    def _normalize_openai_endpoint(cls, v: str) -> str:
        """Accept what the Foundry portal shows and reduce it to the base.

        The portal's "Azure OpenAI endpoint" field reads
        https://<name>.openai.azure.com/openai/v1 -- that is the v1 API surface.
        The AzureOpenAI client wants the bare resource origin and appends the
        rest itself, so pasting the portal value verbatim would otherwise
        produce .../openai/v1/openai/deployments/... and 404.
        """
        v = v.strip().rstrip("/")
        for suffix in ("/openai/v1", "/openai"):
            if v.endswith(suffix):
                v = v[: -len(suffix)]
        return v

    @property
    def semantic_config_name(self) -> str:
        return f"{self.azure_search_index}-semantic"

    def require(self, *names: str) -> None:
        """Fail loudly and early when a needed credential is missing."""
        missing = [n for n in names if not getattr(self, n, None)]
        if missing:
            raise RuntimeError(
                "Missing required settings: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill them in."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
