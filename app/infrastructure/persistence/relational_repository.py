from datetime import datetime

import time

from sqlalchemy import DateTime, Float, Index, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.observability import metrics_registry
from app.core.settings import Settings
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import RelationalTelemetryRepositoryPort


class Base(DeclarativeBase):
    pass


class TelemetryORM(Base):
    __tablename__ = 'telemetry_readings'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    moisture: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    ph: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index('ix_telemetry_device_captured_desc', 'device_id', 'captured_at'),
        Index('ix_telemetry_captured_desc', 'captured_at'),
    )


class SqlAlchemyTelemetryRepository(RelationalTelemetryRepositoryPort):
    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(settings.relational_db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_schema(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save(self, reading: TelemetryReading) -> None:
        started = time.perf_counter()
        try:
            async with self.session_factory() as session:
                session.add(
                    TelemetryORM(
                        device_id=reading.device_id,
                        moisture=reading.moisture,
                        temperature=reading.temperature,
                        ph=reading.ph,
                        captured_at=reading.captured_at,
                    )
                )
                await session.commit()
        except Exception:
            metrics_registry.track_db_query('telemetry.save', time.perf_counter() - started, ok=False)
            raise
        else:
            metrics_registry.track_db_query('telemetry.save', time.perf_counter() - started, ok=True)

    async def list_recent(self, limit: int = 20, device_id: str | None = None) -> list[TelemetryReading]:
        started = time.perf_counter()
        stmt = (
            select(
                TelemetryORM.device_id,
                TelemetryORM.moisture,
                TelemetryORM.temperature,
                TelemetryORM.ph,
                TelemetryORM.captured_at,
            )
            .order_by(TelemetryORM.captured_at.desc())
            .limit(limit)
        )
        if device_id:
            stmt = stmt.where(TelemetryORM.device_id == device_id)

        try:
            async with self.session_factory() as session:
                rows = await session.execute(stmt)
                items = rows.all()
        except Exception:
            metrics_registry.track_db_query('telemetry.list_recent', time.perf_counter() - started, ok=False)
            raise
        else:
            metrics_registry.track_db_query('telemetry.list_recent', time.perf_counter() - started, ok=True)

        return [
            TelemetryReading(
                device_id=item.device_id,
                moisture=item.moisture,
                temperature=item.temperature,
                ph=item.ph,
                captured_at=item.captured_at,
                metadata={},
            )
            for item in items
        ]
