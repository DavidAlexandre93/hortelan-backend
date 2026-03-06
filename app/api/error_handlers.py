import importlib
import importlib.util
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ApiError, InfrastructureError, TransientIntegrationError

logger = logging.getLogger(__name__)


def _otel_available() -> bool:
    return (
        importlib.util.find_spec('opentelemetry.trace') is not None
        and importlib.util.find_spec('opentelemetry') is not None
    )


def _current_trace_context() -> dict[str, str | None]:
    if not _otel_available():
        return {'trace_id': None, 'span_id': None}

    trace = importlib.import_module('opentelemetry.trace')
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if not span_context or not span_context.is_valid:
        return {'trace_id': None, 'span_id': None}

    format_span_id = trace.format_span_id
    format_trace_id = trace.format_trace_id
    return {
        'trace_id': format_trace_id(span_context.trace_id),
        'span_id': format_span_id(span_context.span_id),
    }


def _record_exception_on_span(exc: Exception) -> None:
    if not _otel_available():
        return

    trace = importlib.import_module('opentelemetry.trace')
    status_module = importlib.import_module('opentelemetry.trace.status')

    span = trace.get_current_span()
    if not span:
        return

    span.record_exception(exc)
    span.set_status(status_module.Status(status_module.StatusCode.ERROR, str(exc)))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        trace_context = _current_trace_context()
        body: dict[str, Any] = {
            'error': {
                'code': exc.code,
                'message': exc.message,
                'details': exc.details,
                'path': request.url.path,
                'method': request.method,
                'trace_id': trace_context['trace_id'],
                'span_id': trace_context['span_id'],
            }
        }
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(TransientIntegrationError)
    async def transient_integration_handler(request: Request, exc: TransientIntegrationError) -> JSONResponse:
        trace_context = _current_trace_context()
        body: dict[str, Any] = {
            'error': {
                'code': 'INTEGRATION_TEMPORARY_FAILURE',
                'message': str(exc),
                'details': {},
                'path': request.url.path,
                'method': request.method,
                'trace_id': trace_context['trace_id'],
                'span_id': trace_context['span_id'],
            }
        }
        return JSONResponse(status_code=503, content=body)

    @app.exception_handler(InfrastructureError)
    async def infrastructure_handler(request: Request, exc: InfrastructureError) -> JSONResponse:
        trace_context = _current_trace_context()
        body: dict[str, Any] = {
            'error': {
                'code': 'INFRASTRUCTURE_FAILURE',
                'message': str(exc),
                'details': {},
                'path': request.url.path,
                'method': request.method,
                'trace_id': trace_context['trace_id'],
                'span_id': trace_context['span_id'],
            }
        }
        return JSONResponse(status_code=502, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_context = _current_trace_context()
        _record_exception_on_span(exc)

        logger.exception(
            'Erro não tratado na API',
            extra={
                'path': request.url.path,
                'method': request.method,
                'trace_id': trace_context['trace_id'],
                'span_id': trace_context['span_id'],
                'query_params': str(request.query_params),
            },
        )

        body: dict[str, Any] = {
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'Erro interno inesperado.',
                'details': {'error_type': type(exc).__name__},
                'path': request.url.path,
                'method': request.method,
                'trace_id': trace_context['trace_id'],
                'span_id': trace_context['span_id'],
            }
        }
        return JSONResponse(status_code=500, content=body)
