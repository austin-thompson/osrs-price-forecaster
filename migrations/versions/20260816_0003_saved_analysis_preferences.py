"""Add saved analysis preferences.

Revision ID: 20260816_0003
Revises: 20260816_0002
Create Date: 2026-08-16 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260816_0003"
down_revision: str | None = "20260816_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_analysis_preferences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column(
            "signal_labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "liquidity_statuses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "drift_states",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("top_n", sa.Integer(), nullable=False),
        sa.Column("watchlist_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("horizon_hours > 0", name="ck_saved_preferences_horizon_positive"),
        sa.CheckConstraint("top_n BETWEEN 1 AND 500", name="ck_saved_preferences_top_n_range"),
        sa.ForeignKeyConstraint(
            ["watchlist_id"],
            ["saved_watchlists.id"],
            name="fk_saved_preferences_watchlist_id_saved_watchlists",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_saved_analysis_preferences"),
    )


def downgrade() -> None:
    op.drop_table("saved_analysis_preferences")
