from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import re
import time
import traceback
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.settings import Settings

logger = logging.getLogger(__name__)

request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')
trace_id_ctx: ContextVar[str] = ContextVar('trace_id', default='')
span_id_ctx: ContextVar[str] = ContextVar('span_id', default='')
incident_id_ctx: ContextVar[str] = ContextVar('incident_id', default='')

MAX_LOG_VALUE_LENGTH = 4_096
CORRELATION_ID_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$')
TRACE_ID_PATTERN = re.compile(r'^[0-9a-f]{32}$')
SENSITIVE_KEY_PATTERN = re.compile(
    r'(?i)(authorization|cookie|password|passwd|secret|token|api[_-]?key|private[_-]?key)'
)
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r'(?i)\b(authorization|password|passwd|secret|token|api[_-]?key|private[_-]?key)\b'
    r'(\s*[:=]\s*)([^\s,;]+)'
)
EMAIL_PATTERN = re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')
BEARER_PATTERN = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+')
WINDOWS_USER_PATH_PATTERN = re.compile(r'(?i)([A-Z]:\\Users\\)[^\\\s]+')
POSIX_USER_PATH_PATTERN = re.compile(r'(/(?:home|Users)/)[^/\s]+')
URL_QUERY_PATTERN = re.compile(r'(https?://[^\s?]+)\?[^\s]+')

SAFE_EXTRA_FIELDS = {
    'elapsed_ms',
    'error_code',
    'event',
    'integration',
    'method',
    'operation',
    'path',
    'retryable',
    'route',
    'status_code',
}

OTEL_REQUIRED_MODULES = (
    'opentelemetry',
    'opentelemetry.trace',
    'opentelemetry.exporter.otlp.proto.http.trace_exporter',
    'opentelemetry.instrumentation.fastapi',
    'opentelemetry.sdk.resources',
    'opentelemetry.sdk.trace',
    'opentelemetry.sdk.trace.export',
)
_telemetry_configured = False


def redact_text(value: str) -> str:
    redacted = EMAIL_PATTERN.sub('[REDACTED_EMAIL]', value)
    redacted = BEARER_PATTERN.sub('Bearer [REDACTED]', redacted)
    redacted = SENSITIVE_ASSIGNMENT_PATTERN.sub(r'\1\2[REDACTED]', redacted)
    redacted = WINDOWS_USER_PATH_PATTERN.sub(r'\1[REDACTED]', redacted)
    redacted = POSIX_USER_PATH_PATTERN.sub(r'\1[REDACTED]', redacted)
    redacted = URL_QUERY_PATTERN.sub(r'\1?[REDACTED]', redacted)
    return redacted[:MAX_LOG_VALUE_LENGTH]


def sanitize_log_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, bool | int | float):
        return value
    return redact_text(str(value))


def _has_otel_dependencies() -> bool:
    return all(importlib.util.find_spec(module) is not None for module in OTEL_REQUIRED_MODULES)


def current_trace_context() -> tuple[str | None, str | None]:
    if _has_otel_dependencies():
        trace = importlib.import_module('opentelemetry.trace')
        span_context = trace.get_current_span().get_span_context()
        if span_context and span_context.is_valid:
            return (
                trace.format_trace_id(span_context.trace_id),
                trace.format_span_id(span_context.span_id),
            )

    return trace_id_ctx.get() or None, span_id_ctx.get() or None


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    global _telemetry_configured

    if not settings.otel_enabled:
        logger.info('otel.disabled', extra={'event': 'otel.disabled'})
        return
    if not settings.otel_exporter_otlp_endpoint:
        logger.info('otel.export.disabled', extra={'event': 'otel.export.disabled'})
        return
    if not _has_otel_dependencies():
        logger.error('otel.dependencies.missing', extra={'event': 'otel.dependencies.missing'})
        return
    if _telemetry_configured:
        return

    trace = importlib.import_module('opentelemetry.trace')
    exporter_module = importlib.import_module(
        'opentelemetry.exporter.otlp.proto.http.trace_exporter'
    )
    instrumentation_module = importlib.import_module('opentelemetry.instrumentation.fastapi')
    resource_module = importlib.import_module('opentelemetry.sdk.resources')
    sdk_trace_module = importlib.import_module('opentelemetry.sdk.trace')
    sdk_export_module = importlib.import_module('opentelemetry.sdk.trace.export')

    resource = resource_module.Resource.create(
        {
            'service.name': settings.otel_service_name,
            'service.version': settings.otel_service_version,
            'deployment.environment.name': settings.app_env.value,
        }
    )
    provider = sdk_trace_module.TracerProvider(resource=resource)
    exporter = exporter_module.OTLPSpanExporter(
        endpoint=f'{settings.otel_exporter_otlp_endpoint}/v1/traces',
        timeout=settings.otel_exporter_timeout,
    )
    provider.add_span_processor(sdk_export_module.BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    instrumentation_module.FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls='health/live,metrics',
    )
    _telemetry_configured = True
    logger.info('otel.configured', extra={'event': 'otel.configured'})


def _exception_diagnostics(
    exc_info: tuple[type[BaseException] | None, BaseException | None, Any],
) -> dict[str, str | int | None]:
    exc_type, exc, tb = exc_info
    if exc_type is None or exc is None:
        return {
            'class': 'UnknownException',
            'module': None,
            'file': None,
            'function': None,
            'line': None,
            'message': 'Erro sem diagnostico.',
            'stack': '',
        }
    frames = traceback.extract_tb(tb) if tb else []
    frame = frames[-1] if frames else None
    return {
        'class': exc_type.__name__,
        'module': exc_type.__module__,
        'file': Path(frame.filename).name if frame else None,
        'function': frame.name if frame else None,
        'line': frame.lineno if frame else None,
        'message': redact_text(str(exc)),
        'stack': redact_text(''.join(traceback.format_exception(exc_type, exc, tb))),
    }


class JsonFormatter(logging.Formatter):
    def __init__(
        self,
        service_name: str = 'hortelan-backend',
        environment: str = 'development',
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = current_trace_context()
        payload: dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created, UTC).isoformat(),
            'severity': record.levelname,
            'service': self.service_name,
            'environment': self.environment,
            'logger': record.name,
            'event': redact_text(str(getattr(record, 'event', record.getMessage()))),
            'request_id': request_id_ctx.get() or None,
            'trace_id': trace_id,
            'span_id': span_id,
            'incident_id': incident_id_ctx.get() or None,
        }
        for field_name in SAFE_EXTRA_FIELDS:
            if hasattr(record, field_name):
                payload[field_name] = sanitize_log_value(getattr(record, field_name))
        if record.exc_info:
            payload['exception'] = _exception_diagnostics(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


class MetricsRegistry:
    @dataclass(slots=True)
    class _OperationStats:
        total_seconds: float = 0.0
        count: int = 0
        errors: int = 0
        samples: deque[float] = field(default_factory=lambda: deque(maxlen=2_048))

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time.time()
        self._inflight = 0
        self._request_counter: dict[tuple[str, str, int], int] = defaultdict(int)
        self._latency_counter: dict[tuple[str, str], MetricsRegistry._OperationStats] = defaultdict(
            MetricsRegistry._OperationStats
        )
        self._db_counter: dict[str, MetricsRegistry._OperationStats] = defaultdict(
            MetricsRegistry._OperationStats
        )
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
        self._track_operation(self._db_counter, operation, elapsed_seconds, ok)

    def track_external_call(
        self, integration: str, elapsed_seconds: float, ok: bool = True
    ) -> None:
        self._track_operation(self._external_counter, integration, elapsed_seconds, ok)

    def _track_operation(
        self,
        target: dict[str, MetricsRegistry._OperationStats],
        name: str,
        elapsed_seconds: float,
        ok: bool,
    ) -> None:
        with self._lock:
            stats = target[name]
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
        index = max(0, min(len(ordered) - 1, int(q * (len(ordered) - 1))))
        return ordered[index]

    @staticmethod
    def _escape_label(value: str) -> str:
        return value.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')

    def render_prometheus(self) -> str:
        with self._lock:
            return self._render_locked()

    def _render_locked(self) -> str:
        uptime = max(1e-6, time.time() - self._started_at)
        lines = [
            '# HELP http_server_requests_total Total de requisicoes HTTP processadas.',
            '# TYPE http_server_requests_total counter',
        ]
        for (method, path, status_code), value in sorted(self._request_counter.items()):
            method_label = self._escape_label(method)
            path_label = self._escape_label(path)
            lines.append(
                'http_server_requests_total'
                f'{{method="{method_label}",path="{path_label}",status_code="{status_code}"}} {value}'
            )

        lines.extend(
            [
                '# HELP http_server_inflight_requests Requisicoes HTTP em andamento.',
                '# TYPE http_server_inflight_requests gauge',
                f'http_server_inflight_requests {self._inflight}',
                '# HELP http_server_request_duration_seconds_avg Latencia media por rota.',
                '# TYPE http_server_request_duration_seconds_avg gauge',
                '# HELP http_server_request_duration_seconds_p95 Latencia p95 por rota.',
                '# TYPE http_server_request_duration_seconds_p95 gauge',
                '# HELP http_server_request_duration_seconds_p99 Latencia p99 por rota.',
                '# TYPE http_server_request_duration_seconds_p99 gauge',
                '# HELP http_server_request_error_rate Taxa de erro 5xx por rota.',
                '# TYPE http_server_request_error_rate gauge',
                '# HELP http_server_throughput_rps Throughput medio desde o inicio.',
                '# TYPE http_server_throughput_rps gauge',
                f'http_server_throughput_rps {sum(self._request_counter.values()) / uptime:.6f}',
            ]
        )
        for (method, path), stats in sorted(self._latency_counter.items()):
            labels = f'method="{self._escape_label(method)}",path="{self._escape_label(path)}"'
            average = stats.total_seconds / stats.count if stats.count else 0
            error_rate = stats.errors / stats.count if stats.count else 0
            lines.append(f'http_server_request_duration_seconds_avg{{{labels}}} {average:.6f}')
            lines.append(
                f'http_server_request_duration_seconds_p95{{{labels}}} '
                f'{self._quantile(stats.samples, 0.95):.6f}'
            )
            lines.append(
                f'http_server_request_duration_seconds_p99{{{labels}}} '
                f'{self._quantile(stats.samples, 0.99):.6f}'
            )
            lines.append(f'http_server_request_error_rate{{{labels}}} {error_rate:.6f}')

        self._append_operation_metrics(lines, 'db_query', 'operation', self._db_counter)
        self._append_operation_metrics(
            lines,
            'external_call',
            'integration',
            self._external_counter,
        )
        return '\n'.join(lines) + '\n'

    def _append_operation_metrics(
        self,
        lines: list[str],
        prefix: str,
        label_name: str,
        counters: dict[str, MetricsRegistry._OperationStats],
    ) -> None:
        lines.extend(
            [
                f'# HELP {prefix}_duration_seconds_avg Latencia media por operacao.',
                f'# TYPE {prefix}_duration_seconds_avg gauge',
                f'# HELP {prefix}_duration_seconds_p95 Latencia p95 por operacao.',
                f'# TYPE {prefix}_duration_seconds_p95 gauge',
                f'# HELP {prefix}_errors_total Total de erros por operacao.',
                f'# TYPE {prefix}_errors_total counter',
            ]
        )
        for name, stats in sorted(counters.items()):
            label = self._escape_label(name)
            average = stats.total_seconds / stats.count if stats.count else 0
            labels = f'{label_name}="{label}"'
            lines.append(f'{prefix}_duration_seconds_avg{{{labels}}} {average:.6f}')
            lines.append(
                f'{prefix}_duration_seconds_p95{{{labels}}} '
                f'{self._quantile(stats.samples, 0.95):.6f}'
            )
            lines.append(f'{prefix}_errors_total{{{labels}}} {stats.errors}')


metrics_registry = MetricsRegistry()


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self._lock = Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - 60
        with self._lock:
            queue = self._requests[key]
            while queue and queue[0] < window_start:
                queue.popleft()
            if len(queue) >= self.limit_per_minute:
                return False
            queue.append(now)
            return True


CallNext = Callable[[Request], Awaitable[Response]]


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, logger: logging.Logger, settings: Settings) -> None:
        super().__init__(app)
        self.logger = logger
        self.rate_limiter = RateLimiter(settings.rate_limit_per_minute)

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        request_id = self._request_id(request.headers.get('x-request-id'))
        fallback_trace_id = self._fallback_trace_id(request.headers.get('x-trace-id'))
        fallback_span_id = uuid.uuid4().hex[:16]
        request_token = request_id_ctx.set(request_id)
        trace_token = trace_id_ctx.set(fallback_trace_id)
        span_token = span_id_ctx.set(fallback_span_id)
        incident_token = incident_id_ctx.set('')
        request.state.request_id = request_id
        started = time.perf_counter()
        tracked = False
        response: Response

        try:
            client_host = request.client.host if request.client else 'unknown'
            if not self.rate_limiter.allow(client_host):
                incident_id = uuid.uuid4().hex
                incident_id_ctx.set(incident_id)
                response = self._rate_limited_response(incident_id)
                response.headers['Retry-After'] = '60'
                return self._finalize_response(response, request_id, started)

            metrics_registry.track_start()
            tracked = True
            self.logger.info(
                'http.request.started',
                extra={
                    'event': 'http.request.started',
                    'method': request.method,
                    'path': request.url.path,
                },
            )
            response = await call_next(request)
            route = self._route_template(request)
            elapsed = time.perf_counter() - started
            metrics_registry.track_end(request.method, route, response.status_code, elapsed)
            tracked = False
            self.logger.info(
                'http.request.finished',
                extra={
                    'event': 'http.request.finished',
                    'method': request.method,
                    'route': route,
                    'status_code': response.status_code,
                    'elapsed_ms': round(elapsed * 1_000, 2),
                },
            )
            return self._finalize_response(response, request_id, started)
        except Exception:
            if tracked:
                metrics_registry.track_end(
                    request.method,
                    self._route_template(request),
                    500,
                    time.perf_counter() - started,
                )
            self.logger.exception(
                'http.request.failed',
                extra={
                    'event': 'http.request.failed',
                    'method': request.method,
                    'route': self._route_template(request),
                },
            )
            raise
        finally:
            request_id_ctx.reset(request_token)
            trace_id_ctx.reset(trace_token)
            span_id_ctx.reset(span_token)
            incident_id_ctx.reset(incident_token)

    @staticmethod
    def _request_id(candidate: str | None) -> str:
        if candidate and CORRELATION_ID_PATTERN.fullmatch(candidate):
            return candidate
        return str(uuid.uuid4())

    @staticmethod
    def _fallback_trace_id(candidate: str | None) -> str:
        if candidate and TRACE_ID_PATTERN.fullmatch(candidate):
            return candidate
        return uuid.uuid4().hex

    @staticmethod
    def _route_template(request: Request) -> str:
        route = request.scope.get('route')
        path = getattr(route, 'path', None)
        return str(path) if path else request.url.path

    @staticmethod
    def _rate_limited_response(incident_id: str) -> JSONResponse:
        trace_id, span_id = current_trace_context()
        return JSONResponse(
            status_code=429,
            content={
                'error': {
                    'code': 'RATE_LIMITED',
                    'message': 'Muitas requisicoes. Tente novamente mais tarde.',
                    'retryable': True,
                    'details': {},
                    'diagnostics': {
                        'timestamp': datetime.now(UTC).isoformat(),
                        'status_code': 429,
                        'incident_id': incident_id,
                        'request_id': request_id_ctx.get() or None,
                        'trace_id': trace_id,
                        'span_id': span_id,
                    },
                }
            },
        )

    @staticmethod
    def _finalize_response(response: Response, request_id: str, started: float) -> Response:
        trace_id, span_id = current_trace_context()
        response.headers['x-request-id'] = request_id
        if trace_id:
            response.headers['x-trace-id'] = trace_id
        if span_id:
            response.headers['x-span-id'] = span_id
        response.headers['x-response-time-ms'] = f'{(time.perf_counter() - started) * 1_000:.2f}'
        response.headers['x-content-type-options'] = 'nosniff'
        response.headers['x-frame-options'] = 'DENY'
        response.headers['referrer-policy'] = 'no-referrer'
        response.headers['permissions-policy'] = 'camera=(), geolocation=(), microphone=()'
        response.headers['x-xss-protection'] = '0'
        return response


def configure_logging(settings: Settings) -> logging.Logger:
    app_logger = logging.getLogger('hortelan')
    root = logging.getLogger()
    formatter = JsonFormatter(settings.otel_service_name, settings.app_env.value)

    if not root.handlers:
        stream_handler: logging.Handler = logging.StreamHandler()
        root.addHandler(stream_handler)
    for existing_handler in root.handlers:
        existing_handler.setFormatter(formatter)

    root.setLevel(settings.log_level.value)
    app_logger.setLevel(settings.log_level.value)
    return app_logger
