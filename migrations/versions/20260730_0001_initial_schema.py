"""Initial schema

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("examine", sa.Text(), nullable=True),
        sa.Column("tradeable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("noted_item_id", sa.Integer(), nullable=True),
        sa.Column("high_alch", sa.Integer(), nullable=True),
        sa.Column("low_alch", sa.Integer(), nullable=True),
        sa.Column("limit", sa.Integer(), nullable=True),
        sa.Column("wiki_icon", sa.Text(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_items"),
        sa.UniqueConstraint("item_id", name="uq_items_item_id"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.String(length=32), nullable=False),
        sa.Column("items_requested", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "observations_received", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_runs"),
    )

    op.create_table(
        "forecast_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_forecast_runs"),
    )

    op.create_table(
        "model_evaluations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("evaluation_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_mae", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("metric_rmse", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("metric_smape", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("metric_directional_accuracy", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("metric_bias", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["items.item_id"], name="fk_model_evaluations_item_id_items"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_evaluations"),
    )

    op.create_table(
        "model_selections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column("selected_model_name", sa.String(length=64), nullable=False),
        sa.Column("selected_model_version", sa.String(length=32), nullable=False),
        sa.Column("primary_metric", sa.String(length=32), nullable=False),
        sa.Column("primary_metric_value", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["model_evaluations.id"],
            name="fk_model_selections_evaluation_id_model_evaluations",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["items.item_id"], name="fk_model_selections_item_id_items"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_selections"),
        sa.UniqueConstraint(
            "item_id",
            "horizon_hours",
            "selected_at",
            name="uq_model_selections_item_horizon_selected_at",
        ),
    )

    op.create_table(
        "price_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avg_high_price", sa.Integer(), nullable=True),
        sa.Column("avg_low_price", sa.Integer(), nullable=True),
        sa.Column("high_price_volume", sa.BigInteger(), nullable=True),
        sa.Column("low_price_volume", sa.BigInteger(), nullable=True),
        sa.Column("mid_price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_payload_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name="fk_price_observations_ingestion_run_id_ingestion_runs",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["items.item_id"], name="fk_price_observations_item_id_items"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_price_observations"),
        sa.UniqueConstraint(
            "item_id",
            "interval",
            "source_timestamp",
            name="uq_price_observations_item_interval_source_timestamp",
        ),
    )
    op.create_index(
        "idx_price_observations_ingested_at",
        "price_observations",
        ["ingested_at"],
        unique=False,
    )
    op.create_index(
        "idx_price_observations_item_interval_source_ts",
        "price_observations",
        ["item_id", "interval", "source_timestamp"],
        unique=False,
    )

    op.create_table(
        "forecasts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("forecast_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_target_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_mid_price", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("training_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("training_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("forecast_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(
            ["forecast_run_id"],
            ["forecast_runs.id"],
            name="fk_forecasts_forecast_run_id_forecast_runs",
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"], name="fk_forecasts_item_id_items"),
        sa.PrimaryKeyConstraint("id", name="pk_forecasts"),
        sa.UniqueConstraint(
            "item_id",
            "horizon_hours",
            "forecast_created_at",
            "forecast_target_at",
            "model_name",
            "model_version",
            name="uq_forecasts_item_horizon_created_target_model",
        ),
    )


def downgrade() -> None:
    op.drop_table("forecasts")
    op.drop_index("idx_price_observations_item_interval_source_ts", table_name="price_observations")
    op.drop_index("idx_price_observations_ingested_at", table_name="price_observations")
    op.drop_table("price_observations")
    op.drop_table("model_selections")
    op.drop_table("model_evaluations")
    op.drop_table("forecast_runs")
    op.drop_table("ingestion_runs")
    op.drop_table("items")
