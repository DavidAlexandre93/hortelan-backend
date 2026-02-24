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
import json
import logging
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar
from threading import Lock
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')
trace_id_ctx: ContextVar[str] = ContextVar('trace_id', default='')
span_id_ctx: ContextVar[str] = ContextVar('span_id', default='')


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': self.formatTime(record, datefmt='%Y-%m-%dT%H:%M:%S%z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': request_id_ctx.get(),
            'trace_id': trace_id_ctx.get(),
            'span_id': span_id_ctx.get(),
        }
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._inflight = 0
        self._request_counter: dict[tuple[str, str, int], int] = defaultdict(int)
        self._latency_counter: dict[tuple[str, str], tuple[float, int]] = defaultdict(lambda: (0.0, 0))

    def track_start(self) -> None:
        with self._lock:
            self._inflight += 1

    def track_end(self, method: str, path: str, status_code: int, elapsed_seconds: float) -> None:
        with self._lock:
            self._inflight = max(0, self._inflight - 1)
            self._request_counter[(method, path, status_code)] += 1
            total, count = self._latency_counter[(method, path)]
            self._latency_counter[(method, path)] = (total + elapsed_seconds, count + 1)

    def render_prometheus(self) -> str:
        lines = [
            '# HELP http_server_requests_total Total de requisições HTTP processadas.',
            '# TYPE http_server_requests_total counter',
        ]
        for (method, path, status_code), value in sorted(self._request_counter.items()):
            lines.append(
                f'http_server_requests_total{{method="{method}",path="{path}",status_code="{status_code}"}} {value}'
            )

        lines.extend(
            [
                '# HELP http_server_inflight_requests Requisições HTTP em andamento.',
                '# TYPE http_server_inflight_requests gauge',
                f'http_server_inflight_requests {self._inflight}',
                '# HELP http_server_request_duration_seconds_avg Latência média das requisições por rota.',
                '# TYPE http_server_request_duration_seconds_avg gauge',
            ]
        )
        for (method, path), (total, count) in sorted(self._latency_counter.items()):
            avg = total / count if count else 0
            lines.append(
                f'http_server_request_duration_seconds_avg{{method="{method}",path="{path}"}} {avg:.6f}'
            )

        return '\n'.join(lines) + '\n'


metrics_registry = MetricsRegistry()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get('x-request-id', str(uuid.uuid4()))
        trace_id = request.headers.get('x-trace-id', uuid.uuid4().hex)
        span_id = uuid.uuid4().hex[:16]

        request_id_ctx.set(request_id)
        trace_id_ctx.set(trace_id)
        span_id_ctx.set(span_id)
        metrics_registry.track_start()

        started = time.perf_counter()
        path_template = request.scope.get('route').path if request.scope.get('route') else request.url.path

        self.logger.info('request_started', extra={'method': request.method, 'path': request.url.path})
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            elapsed = time.perf_counter() - started
            metrics_registry.track_end(request.method, path_template, 500, elapsed)
            self.logger.exception('request_failed')
            raise

        elapsed = time.perf_counter() - started
        metrics_registry.track_end(request.method, path_template, status_code, elapsed)

        response.headers['x-request-id'] = request_id
        response.headers['x-trace-id'] = trace_id
        response.headers['x-span-id'] = span_id
        response.headers['x-response-time-ms'] = f'{elapsed * 1000:.2f}'

        self.logger.info(
            'request_finished',
            extra={
                'method': request.method,
                'path': request.url.path,
                'status_code': status_code,
                'elapsed_ms': round(elapsed * 1000, 2),
            },
        )
        return response


def configure_logging(level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger('hortelan')
    root = logging.getLogger()

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())

    root.setLevel(level.upper())
    logger.setLevel(level.upper())
    return logger
