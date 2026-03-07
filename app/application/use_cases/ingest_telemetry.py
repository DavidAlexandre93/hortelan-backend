"""Compat: mantenha import legado.

Novo caminho recomendado:
app.application.use_cases.iot.ingest_telemetry_use_case.IngestTelemetryUseCase
"""

from app.application.use_cases.iot.ingest_telemetry_use_case import IngestTelemetryUseCase

__all__ = ['IngestTelemetryUseCase']
