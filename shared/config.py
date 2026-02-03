from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_project_root() -> Path:
    """Return the project root directory (parent of shared/)."""

    return Path(__file__).parent.parent


class RagSettings(BaseSettings):
    """Configuration for RAG agent and Chroma vector store."""

    model_config = SettingsConfigDict(env_prefix="RAG_")

    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "movies"
    chroma_persist_dir: str = "setup/summary_data/chroma"

    @model_validator(mode="after")
    def resolve_paths(self) -> "RagSettings":
        """Convert relative paths to absolute paths anchored at project root."""

        if not Path(self.chroma_persist_dir).is_absolute():
            resolved = _get_project_root() / self.chroma_persist_dir
            object.__setattr__(self, "chroma_persist_dir", str(resolved))

        return self


class TelemetrySettings(BaseSettings):
    """Configuration for OpenTelemetry/Jaeger."""

    model_config = SettingsConfigDict(env_prefix="TELEMETRY_")
    service_name: str = "movie-recommendation-agent"
    jaeger_endpoint: str = "http://localhost:4317"
    jaeger_ui_url: str = "http://localhost:16686"


class Settings(BaseSettings):
    """Root settings container - aggregates all config sections."""

    rag: RagSettings = RagSettings()
    telemetry: TelemetrySettings = TelemetrySettings()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance. Call once at startup."""

    return Settings()
