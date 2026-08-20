from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, String, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.exceptions import InfrastructureError
from app.core.observability import metrics_registry
from app.core.settings import Settings
from app.domain.entities.models import (
    IdempotencyRecord,
    IdempotencyState,
    OutboxEvent,
    OutboxState,
    TelemetryReading,
)
from app.domain.ports.interfaces import (
    IdempotencyRepositoryPort,
    RelationalTelemetryRepositoryPort,
)


class Base(DeclarativeBase):
    pass


class TelemetryORM(Base):
    __tablename__ = 'telemetry_readings'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    moisture: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    ph: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('ix_telemetry_device_captured_desc', 'device_id', 'captured_at'),
        Index('ix_telemetry_captured_desc', 'captured_at'),
    )


class IdempotencyORM(Base):
    __tablename__ = 'idempotency_records'

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class OutboxORM(Base):
    __tablename__ = 'outbox_events'

    event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column('payload', JSON, nullable=False)
    state: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)


class SqlAlchemyTelemetryRepository(RelationalTelemetryRepositoryPort, IdempotencyRepositoryPort):
    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(
            settings.relational_db_url, echo=False, pool_pre_ping=True
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def init_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text('SELECT 1'))

    async def save_with_outbox(self, reading: TelemetryReading) -> str:
        started = time.perf_counter()
        event_id = uuid.uuid4().hex
        try:
            async with self.session_factory.begin() as session:
                session.add(
                    TelemetryORM(
                        device_id=reading.device_id,
                        moisture=reading.moisture,
                        temperature=reading.temperature,
                        ph=reading.ph,
                        captured_at=reading.captured_at,
                        metadata_json=reading.metadata,
                    )
                )
                session.add(
                    OutboxORM(
                        event_id=event_id,
                        event_type='telemetry.ingested',
                        aggregate_id=reading.device_id,
                        payload_json={
                            'device_id': reading.device_id,
                            'moisture': reading.moisture,
                            'temperature': reading.temperature,
                            'ph': reading.ph,
                            'captured_at': reading.captured_at.isoformat(),
                            'metadata': reading.metadata,
                        },
                        state=OutboxState.PENDING.value,
                        occurred_at=reading.captured_at,
                    )
                )
        except Exception as exc:
            metrics_registry.track_db_query(
                'telemetry.save', time.perf_counter() - started, ok=False
            )
            raise InfrastructureError('Falha ao persistir telemetria') from exc
        metrics_registry.track_db_query('telemetry.save', time.perf_counter() - started)
        return event_id

    async def list_recent(
        self,
        limit: int = 20,
        device_id: str | None = None,
    ) -> list[TelemetryReading]:
        started = time.perf_counter()
        statement = select(TelemetryORM).order_by(TelemetryORM.captured_at.desc()).limit(limit)
        if device_id:
            statement = statement.where(TelemetryORM.device_id == device_id)

        try:
            async with self.session_factory() as session:
                items = (await session.scalars(statement)).all()
        except Exception as exc:
            metrics_registry.track_db_query(
                'telemetry.list_recent',
                time.perf_counter() - started,
                ok=False,
            )
            raise InfrastructureError('Falha ao consultar telemetria') from exc
        metrics_registry.track_db_query('telemetry.list_recent', time.perf_counter() - started)

        return [
            TelemetryReading(
                device_id=item.device_id,
                moisture=item.moisture,
                temperature=item.temperature,
                ph=item.ph,
                captured_at=self._as_utc(item.captured_at),
                metadata=item.metadata_json,
            )
            for item in items
        ]

    async def list_pending_outbox(self, limit: int = 100) -> list[OutboxEvent]:
        statement = (
            select(OutboxORM)
            .where(OutboxORM.state == OutboxState.PENDING.value)
            .order_by(OutboxORM.occurred_at)
            .limit(limit)
        )
        async with self.session_factory() as session:
            items = (await session.scalars(statement)).all()
        return [
            OutboxEvent(
                event_id=item.event_id,
                event_type=item.event_type,
                aggregate_id=item.aggregate_id,
                payload=item.payload_json,
                state=OutboxState(item.state),
                occurred_at=self._as_utc(item.occurred_at),
                attempt_count=item.attempt_count,
            )
            for item in items
        ]

    async def mark_outbox_published(self, event_id: str) -> None:
        async with self.session_factory.begin() as session:
            existing = await session.get(OutboxORM, event_id)
            if existing is None:
                raise InfrastructureError('Evento outbox inexistente')
            existing.state = OutboxState.PUBLISHED.value
            existing.attempt_count += 1

    async def reserve(self, record: IdempotencyRecord) -> tuple[bool, IdempotencyRecord]:
        started = time.perf_counter()
        try:
            async with self.session_factory.begin() as session:
                session.add(
                    IdempotencyORM(
                        key=record.key,
                        operation=record.operation,
                        fingerprint=record.fingerprint,
                        state=record.state.value,
                    )
                )
                await session.flush()
        except IntegrityError:
            existing = await self._get_idempotency(record.key)
            metrics_registry.track_db_query('idempotency.reserve', time.perf_counter() - started)
            return False, existing
        except Exception as exc:
            metrics_registry.track_db_query(
                'idempotency.reserve',
                time.perf_counter() - started,
                ok=False,
            )
            raise InfrastructureError('Falha ao reservar idempotencia') from exc

        metrics_registry.track_db_query('idempotency.reserve', time.perf_counter() - started)
        return True, record

    async def complete(self, key: str, response: dict[str, Any]) -> None:
        await self._update_idempotency(key, IdempotencyState.COMPLETED, response)

    async def mark_unknown(self, key: str) -> None:
        await self._update_idempotency(key, IdempotencyState.UNKNOWN, None)

    async def _get_idempotency(self, key: str) -> IdempotencyRecord:
        async with self.session_factory() as session:
            existing = await session.get(IdempotencyORM, key)
        if existing is None:
            raise InfrastructureError('Reserva de idempotencia nao encontrada apos conflito')
        return IdempotencyRecord(
            key=existing.key,
            operation=existing.operation,
            fingerprint=existing.fingerprint,
            state=IdempotencyState(existing.state),
            response=existing.response_json,
        )

    async def _update_idempotency(
        self,
        key: str,
        state: IdempotencyState,
        response: dict[str, Any] | None,
    ) -> None:
        started = time.perf_counter()
        try:
            async with self.session_factory.begin() as session:
                existing = await session.get(IdempotencyORM, key)
                if existing is None:
                    raise InfrastructureError('Reserva de idempotencia inexistente')
                existing.state = state.value
                existing.response_json = response
                existing.updated_at = datetime.now(UTC)
        except InfrastructureError:
            metrics_registry.track_db_query(
                'idempotency.update', time.perf_counter() - started, ok=False
            )
            raise
        except Exception as exc:
            metrics_registry.track_db_query(
                'idempotency.update', time.perf_counter() - started, ok=False
            )
            raise InfrastructureError('Falha ao atualizar idempotencia') from exc
        metrics_registry.track_db_query('idempotency.update', time.perf_counter() - started)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
