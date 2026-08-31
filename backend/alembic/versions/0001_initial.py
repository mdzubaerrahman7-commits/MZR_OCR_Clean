"""Initial schema for the Import Audit module.

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01

Generated from the SQLAlchemy models via Base.metadata rather than hand-typed
op.create_table calls, specifically to avoid the schema drifting from
app/models/*.py — the models are the single source of truth for column types,
nullability and foreign keys, and duplicating them by hand in this file would be
exactly the kind of silent-drift risk the spec's evidence rules warn against
elsewhere. Once this baseline is applied against a real database, use
`alembic revision --autogenerate` for every subsequent change so future
migrations diff against actual DB state instead.
"""

from typing import Sequence, Union

from alembic import op

from app.db.base import Base
from app.models import *  # noqa: F401,F403 — register every model on Base.metadata

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
