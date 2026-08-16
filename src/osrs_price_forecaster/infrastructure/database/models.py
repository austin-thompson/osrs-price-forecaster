import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from osrs_price_forecaster.infrastructure.database.base import Base


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    examine: Mapped[str | None] = mapped_column(Text, nullable=True)
    tradeable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    noted_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_alch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    low_alch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wiki_icon: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavedWatchlistModel(Base):
    __tablename__ = "saved_watchlists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    item_ids: Mapped[list[int]] = mapped_column("item_ids", JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class SavedAnalysisPreferenceModel(Base):
    __tablename__ = "saved_analysis_preferences"
    __table_args__ = (
        CheckConstraint("horizon_hours > 0", name="ck_saved_preferences_horizon_positive"),
        CheckConstraint("top_n BETWEEN 1 AND 500", name="ck_saved_preferences_top_n_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_labels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    liquidity_statuses: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    drift_states: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    top_n: Mapped[int] = mapped_column(Integer, nullable=False)
    watchlist_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "saved_watchlists.id",
            name="fk_saved_preferences_watchlist_id_saved_watchlists",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class IngestionRunModel(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(32), nullable=False)
    items_requested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observations_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


class PriceObservationModel(Base):
    __tablename__ = "price_observations"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "interval",
            "source_timestamp",
            name="uq_price_observations_item_interval_source_timestamp",
        ),
        Index(
            "idx_price_observations_item_interval_source_ts",
            "item_id",
            "interval",
            "source_timestamp",
        ),
        Index("idx_price_observations_ingested_at", "ingested_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("items.item_id", name="fk_price_observations_item_id_items"),
        nullable=False,
    )
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    avg_high_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_low_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_price_volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    low_price_volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mid_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "ingestion_runs.id", name="fk_price_observations_ingestion_run_id_ingestion_runs"
        ),
        nullable=True,
    )
    source_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ForecastRunModel(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class ForecastModel(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "horizon_hours",
            "forecast_created_at",
            "forecast_target_at",
            "model_name",
            "model_version",
            name="uq_forecasts_item_horizon_created_target_model",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.item_id", name="fk_forecasts_item_id_items"), nullable=False
    )
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    forecast_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_target_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_mid_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    training_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    training_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    forecast_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("forecast_runs.id", name="fk_forecasts_forecast_run_id_forecast_runs"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class ModelEvaluationModel(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("items.item_id", name="fk_model_evaluations_item_id_items"),
        nullable=False,
    )
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluation_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    evaluation_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric_mae: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    metric_rmse: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    metric_smape: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    metric_directional_accuracy: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    metric_bias: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class ModelSelectionModel(Base):
    __tablename__ = "model_selections"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "horizon_hours",
            "selected_at",
            name="uq_model_selections_item_horizon_selected_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("items.item_id", name="fk_model_selections_item_id_items"),
        nullable=False,
    )
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_metric_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "model_evaluations.id", name="fk_model_selections_evaluation_id_model_evaluations"
        ),
        nullable=True,
    )
