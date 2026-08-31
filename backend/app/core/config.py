from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration.

    DATABASE_URL points at PostgreSQL in every real environment (Supabase Postgres
    recommended by the spec); it defaults to a local SQLite file only so the app can
    boot without any infrastructure for a quick smoke test. Tests override it with
    an in-memory SQLite database via the `db_session` fixture.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BondAudit Platform - Import Audit"
    environment: str = "development"

    database_url: str = "sqlite:///./bondaudit_dev.db"

    jwt_secret_key: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    storage_backend: str = "local"  # "local" or "s3"
    storage_local_root: str = "./evidence_storage"

    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
