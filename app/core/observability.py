import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.settings import Settings

logger = logging.getLogger(__name__)


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    if not settings.otel_enabled:
        logger.info('OpenTelemetry desabilitado por configuração.')
        return

    resource = Resource.create(
        {
            'service.name': settings.otel_service_name,
            'service.version': settings.otel_service_version,
            'deployment.environment': settings.app_env,
        }
    )

    tracer_provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            timeout=settings.otel_exporter_timeout,
        )
    else:
        exporter = ConsoleSpanExporter()
        logger.warning('OTEL endpoint não configurado; exportando spans no console.')

    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(app)
    logger.info('OpenTelemetry inicializado para FastAPI.')
