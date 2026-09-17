from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Rewrite a driver-less PostgreSQL URL to explicitly use the psycopg (3.x) driver.

    Render (and most other hosts) inject DATABASE_URL as `postgres://...` or
    `postgresql://...`. SQLAlchemy's default dialect for both of those is psycopg2,
    which this project does not install (it pins `psycopg[binary]` — psycopg 3.x, per
    requirements.txt and .env.example) — left unrewritten, engine creation fails with
    `ModuleNotFoundError: No module named 'psycopg2'`. Any URL that already names a
    driver (`postgresql+psycopg://`, `sqlite://`, ...) is passed through unchanged.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


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

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        return normalize_database_url(v)

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
