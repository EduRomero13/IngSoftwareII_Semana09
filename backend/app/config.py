from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SOC-Lite"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://soclite:soclite@localhost:5432/soclite"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    webhook_token: str = "soclite-webhook-token"

    # LLM
    llm_provider: str = "ollama"  # ollama | none
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    llm_timeout_seconds: float = 60.0
    triage_fallback_enabled: bool = True

    # Enrichment APIs (opcional; sin key => modo simulado)
    virustotal_api_key: str = ""
    abuseipdb_api_key: str = ""
    enrichment_mock: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
