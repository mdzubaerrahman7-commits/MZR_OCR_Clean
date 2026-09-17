from sqlalchemy import create_engine

from app.core.config import Settings, normalize_database_url


def test_normalizes_bare_postgres_scheme():
    assert (
        normalize_database_url("postgres://user:pass@host.render.com:5432/db")
        == "postgresql+psycopg://user:pass@host.render.com:5432/db"
    )


def test_normalizes_bare_postgresql_scheme():
    assert (
        normalize_database_url("postgresql://user:pass@host.render.com:5432/db")
        == "postgresql+psycopg://user:pass@host.render.com:5432/db"
    )


def test_preserves_query_string():
    assert (
        normalize_database_url("postgres://user:pass@host/db?sslmode=require")
        == "postgresql+psycopg://user:pass@host/db?sslmode=require"
    )


def test_leaves_explicit_driver_untouched():
    url = "postgresql+psycopg2://user:pass@host:5432/db"
    assert normalize_database_url(url) == url


def test_leaves_sqlite_untouched():
    url = "sqlite:///./bondaudit_dev.db"
    assert normalize_database_url(url) == url


def test_settings_applies_normalization_to_database_url():
    settings = Settings(database_url="postgres://user:pass@host:5432/db")
    assert settings.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_normalized_url_resolves_to_installed_psycopg_driver():
    """Regression test for the Render deploy failure: ModuleNotFoundError: No module
    named 'psycopg2' — a driver-less URL must resolve to the psycopg (3.x) driver
    that requirements.txt actually installs, not SQLAlchemy's psycopg2 default."""
    engine = create_engine(normalize_database_url("postgres://user:pass@host:5432/db"))
    assert engine.dialect.driver == "psycopg"
