import importlib
import importlib.util
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ApiError, InfrastructureError, TransientIntegrationError
from app.core.observability import request_id_ctx
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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


def _build_error_response(
    *,
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    exc: Exception | None = None,
) -> JSONResponse:
    trace_context = _current_trace_context()
    diagnostics: dict[str, Any] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status_code': status_code,
        'path': request.url.path,
        'method': request.method,
        'request_id': request_id_ctx.get() or None,
        'trace_id': trace_context['trace_id'],
        'span_id': trace_context['span_id'],
    }

    if exc is not None:
        diagnostics['error_type'] = type(exc).__name__

        if exc.__cause__:
            diagnostics['root_cause'] = {
                'type': type(exc.__cause__).__name__,
                'message': str(exc.__cause__),
            }

        should_expose_traceback = settings.app_env.lower() != 'production'
        if should_expose_traceback:
            diagnostics['traceback'] = traceback.format_exception(type(exc), exc, exc.__traceback__)

    body = {
        'error': {
            'code': code,
            'message': message,
            'details': details or {},
            'diagnostics': diagnostics,
        }
    }
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return _build_error_response(
            request=request,
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            exc=exc,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _build_error_response(
            request=request,
            code='VALIDATION_ERROR',
            message='Dados de entrada inválidos.',
            status_code=422,
            details={'errors': exc.errors()},
            exc=exc,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _build_error_response(
            request=request,
            code='HTTP_ERROR',
            message=str(exc.detail),
            status_code=exc.status_code,
            details={},
            exc=exc,
        )

    @app.exception_handler(TransientIntegrationError)
    async def transient_integration_handler(request: Request, exc: TransientIntegrationError) -> JSONResponse:
        return _build_error_response(
            request=request,
            code='INTEGRATION_TEMPORARY_FAILURE',
            message=str(exc),
            status_code=503,
            details={},
            exc=exc,
        )

    @app.exception_handler(InfrastructureError)
    async def infrastructure_handler(request: Request, exc: InfrastructureError) -> JSONResponse:
        return _build_error_response(
            request=request,
            code='INFRASTRUCTURE_FAILURE',
            message=str(exc),
            status_code=502,
            details={},
            exc=exc,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_exception_on_span(exc)

        logger.exception(
            'Erro não tratado na API',
            extra={
                'path': request.url.path,
                'method': request.method,
                'trace_id': _current_trace_context()['trace_id'],
                'span_id': _current_trace_context()['span_id'],
                'query_params': str(request.query_params),
            },
        )
        return _build_error_response(
            request=request,
            code='INTERNAL_SERVER_ERROR',
            message='Erro interno inesperado.',
            status_code=500,
            details={'error_type': type(exc).__name__},
            exc=exc,
        )
