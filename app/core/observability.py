import importlib
import importlib.util
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from contextvars import ContextVar
from threading import Lock
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.settings import Settings

logger = logging.getLogger(__name__)

request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')
trace_id_ctx: ContextVar[str] = ContextVar('trace_id', default='')
span_id_ctx: ContextVar[str] = ContextVar('span_id', default='')


OTEL_REQUIRED_MODULES = (
    'opentelemetry',
    'opentelemetry.trace',
    'opentelemetry.exporter.otlp.proto.http.trace_exporter',
    'opentelemetry.instrumentation.fastapi',
    'opentelemetry.sdk.resources',
    'opentelemetry.sdk.trace',
    'opentelemetry.sdk.trace.export',
)


def _has_otel_dependencies() -> bool:
    return all(importlib.util.find_spec(module) is not None for module in OTEL_REQUIRED_MODULES)


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    if not settings.otel_enabled:
        logger.info('OpenTelemetry desabilitado por configuração.')
        return

    if not _has_otel_dependencies():
        logger.warning('OpenTelemetry habilitado, mas dependências não estão instaladas. Telemetria desativada.')
        return

    trace = importlib.import_module('opentelemetry.trace')
    trace_exporter_module = importlib.import_module('opentelemetry.exporter.otlp.proto.http.trace_exporter')
    instrumentation_module = importlib.import_module('opentelemetry.instrumentation.fastapi')
    resource_module = importlib.import_module('opentelemetry.sdk.resources')
    sdk_trace_module = importlib.import_module('opentelemetry.sdk.trace')
    sdk_export_module = importlib.import_module('opentelemetry.sdk.trace.export')

    resource = resource_module.Resource.create(
        {
            'service.name': settings.otel_service_name,
            'service.version': settings.otel_service_version,
            'deployment.environment': settings.app_env,
        }
    )

    tracer_provider = sdk_trace_module.TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        exporter = trace_exporter_module.OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            timeout=settings.otel_exporter_timeout,
        )
    else:
        exporter = sdk_export_module.ConsoleSpanExporter()
        logger.warning('OTEL endpoint não configurado; exportando spans no console.')

    tracer_provider.add_span_processor(sdk_export_module.BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    instrumentation_module.FastAPIInstrumentor.instrument_app(app)
    logger.info('OpenTelemetry inicializado para FastAPI.')


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
    @dataclass
    class _OperationStats:
        total_seconds: float = 0.0
        count: int = 0
        errors: int = 0
        samples: deque[float] = field(default_factory=lambda: deque(maxlen=2048))

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time.time()
        self._inflight = 0
        self._request_counter: dict[tuple[str, str, int], int] = defaultdict(int)
        self._latency_counter: dict[tuple[str, str], MetricsRegistry._OperationStats] = defaultdict(
            MetricsRegistry._OperationStats
        )
        self._db_counter: dict[str, MetricsRegistry._OperationStats] = defaultdict(MetricsRegistry._OperationStats)
        self._external_counter: dict[str, MetricsRegistry._OperationStats] = defaultdict(
            MetricsRegistry._OperationStats
        )

    def track_start(self) -> None:
        with self._lock:
            self._inflight += 1

    def track_end(self, method: str, path: str, status_code: int, elapsed_seconds: float) -> None:
        with self._lock:
            self._inflight = max(0, self._inflight - 1)
            self._request_counter[(method, path, status_code)] += 1
            stats = self._latency_counter[(method, path)]
            stats.total_seconds += elapsed_seconds
            stats.count += 1
            stats.samples.append(elapsed_seconds)
            if status_code >= 500:
                stats.errors += 1

    def track_db_query(self, operation: str, elapsed_seconds: float, ok: bool = True) -> None:
        with self._lock:
            stats = self._db_counter[operation]
            stats.total_seconds += elapsed_seconds
            stats.count += 1
            stats.samples.append(elapsed_seconds)
            if not ok:
                stats.errors += 1

    def track_external_call(self, integration: str, elapsed_seconds: float, ok: bool = True) -> None:
        with self._lock:
            stats = self._external_counter[integration]
            stats.total_seconds += elapsed_seconds
            stats.count += 1
            stats.samples.append(elapsed_seconds)
            if not ok:
                stats.errors += 1

    @staticmethod
    def _quantile(samples: deque[float], q: float) -> float:
        if not samples:
            return 0.0
        ordered = sorted(samples)
        idx = max(0, min(len(ordered) - 1, int(q * (len(ordered) - 1))))
        return ordered[idx]

    def render_prometheus(self) -> str:
        uptime = max(1e-6, time.time() - self._started_at)
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
                '# HELP http_server_request_duration_seconds_p95 Latência p95 das requisições por rota.',
                '# TYPE http_server_request_duration_seconds_p95 gauge',
                '# HELP http_server_request_duration_seconds_p99 Latência p99 das requisições por rota.',
                '# TYPE http_server_request_duration_seconds_p99 gauge',
                '# HELP http_server_request_error_rate Taxa de erro 5xx por rota.',
                '# TYPE http_server_request_error_rate gauge',
                '# HELP http_server_throughput_rps Throughput médio em requests por segundo desde o início do processo.',
                '# TYPE http_server_throughput_rps gauge',
            ]
        )
        total_requests = sum(self._request_counter.values())
        lines.append(f'http_server_throughput_rps {total_requests / uptime:.6f}')

        for (method, path), stats in sorted(self._latency_counter.items()):
            avg = stats.total_seconds / stats.count if stats.count else 0
            p95 = self._quantile(stats.samples, 0.95)
            p99 = self._quantile(stats.samples, 0.99)
            error_rate = stats.errors / stats.count if stats.count else 0
            lines.append(f'http_server_request_duration_seconds_avg{{method="{method}",path="{path}"}} {avg:.6f}')
            lines.append(f'http_server_request_duration_seconds_p95{{method="{method}",path="{path}"}} {p95:.6f}')
            lines.append(f'http_server_request_duration_seconds_p99{{method="{method}",path="{path}"}} {p99:.6f}')
            lines.append(f'http_server_request_error_rate{{method="{method}",path="{path}"}} {error_rate:.6f}')

        lines.extend(
            [
                '# HELP db_query_duration_seconds_avg Latência média por operação de banco.',
                '# TYPE db_query_duration_seconds_avg gauge',
                '# HELP db_query_duration_seconds_p95 Latência p95 por operação de banco.',
                '# TYPE db_query_duration_seconds_p95 gauge',
                '# HELP db_query_errors_total Total de erros por operação de banco.',
                '# TYPE db_query_errors_total counter',
            ]
        )
        for operation, stats in sorted(self._db_counter.items()):
            avg = stats.total_seconds / stats.count if stats.count else 0
            p95 = self._quantile(stats.samples, 0.95)
            lines.append(f'db_query_duration_seconds_avg{{operation="{operation}"}} {avg:.6f}')
            lines.append(f'db_query_duration_seconds_p95{{operation="{operation}"}} {p95:.6f}')
            lines.append(f'db_query_errors_total{{operation="{operation}"}} {stats.errors}')

        lines.extend(
            [
                '# HELP external_call_duration_seconds_avg Latência média por integração externa.',
                '# TYPE external_call_duration_seconds_avg gauge',
                '# HELP external_call_duration_seconds_p95 Latência p95 por integração externa.',
                '# TYPE external_call_duration_seconds_p95 gauge',
                '# HELP external_call_errors_total Total de erros por integração externa.',
                '# TYPE external_call_errors_total counter',
            ]
        )
        for integration, stats in sorted(self._external_counter.items()):
            avg = stats.total_seconds / stats.count if stats.count else 0
            p95 = self._quantile(stats.samples, 0.95)
            lines.append(f'external_call_duration_seconds_avg{{integration="{integration}"}} {avg:.6f}')
            lines.append(f'external_call_duration_seconds_p95{{integration="{integration}"}} {p95:.6f}')
            lines.append(f'external_call_errors_total{{integration="{integration}"}} {stats.errors}')

        return '\n'.join(lines) + '\n'


metrics_registry = MetricsRegistry()


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self._lock = Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60
        with self._lock:
            queue = self._requests[key]
            while queue and queue[0] < window_start:
                queue.popleft()
            if len(queue) >= self.limit_per_minute:
                return False
            queue.append(now)
        return True


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, logger: logging.Logger, settings: Settings):
        super().__init__(app)
        self.logger = logger
        self.rate_limiter = RateLimiter(settings.rate_limit_per_minute)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get('x-request-id', str(uuid.uuid4()))
        trace_id = request.headers.get('x-trace-id', uuid.uuid4().hex)
        span_id = uuid.uuid4().hex[:16]

        request_id_ctx.set(request_id)
        trace_id_ctx.set(trace_id)
        span_id_ctx.set(span_id)

        client_host = request.client.host if request.client else 'unknown'
        if not self.rate_limiter.allow(client_host):
            response = Response('rate limit exceeded', status_code=429)
            response.headers['Retry-After'] = '60'
            return response

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
        response.headers['x-content-type-options'] = 'nosniff'
        response.headers['x-frame-options'] = 'DENY'
        response.headers['referrer-policy'] = 'no-referrer'
        response.headers['x-xss-protection'] = '0'

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
    app_logger = logging.getLogger('hortelan')
    root = logging.getLogger()

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())

    root.setLevel(level.upper())
    app_logger.setLevel(level.upper())
    return app_logger
