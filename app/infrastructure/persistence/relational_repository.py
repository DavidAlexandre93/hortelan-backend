from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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


class SqlAlchemyTelemetryRepository(RelationalTelemetryRepositoryPort):
    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(settings.relational_db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_schema(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save(self, reading: TelemetryReading) -> None:
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
