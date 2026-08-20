from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.contracts.errors import (
    ErrorBodyOut,
    ErrorDiagnosticsOut,
    ErrorEnvelopeOut,
    ValidationIssueOut,
)
from app.core.exceptions import ApiError, ErrorCode, InfrastructureError, TransientIntegrationError
from app.core.observability import (
    current_trace_context,
    incident_id_ctx,
    redact_text,
    request_id_ctx,
)

logger = logging.getLogger(__name__)
SENSITIVE_DETAIL_KEYS = {'authorization', 'email', 'password', 'secret', 'token', 'api_key'}


def _current_trace_context() -> dict[str, str | None]:
    trace_id, span_id = current_trace_context()
    return {'trace_id': trace_id, 'span_id': span_id}


def _record_exception_on_span(exc: Exception) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode
    except ImportError:
        return

    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR))


def _sanitize_public_value(value: Any, depth: int = 0) -> Any:
    if depth >= 5:
        return '[TRUNCATED]'
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return redact_text(value)[:256]
    if isinstance(value, list | tuple):
        return [_sanitize_public_value(item, depth + 1) for item in value[:50]]
    if isinstance(value, dict):
        return {
            str(key)[:64]: (
                '[REDACTED]'
                if str(key).lower() in SENSITIVE_DETAIL_KEYS
                else _sanitize_public_value(item, depth + 1)
            )
            for key, item in list(value.items())[:50]
        }
    return str(type(value).__name__)[:64]


def _sanitize_public_details(details: dict[str, Any] | None) -> dict[str, Any]:
    sanitized = _sanitize_public_value(details or {})
    return sanitized if isinstance(sanitized, dict) else {}


def _validation_details(exc: RequestValidationError) -> dict[str, Any]:
    issues = [
        ValidationIssueOut(
            location=list(error.get('loc', ())),
            kind=str(error.get('type', 'validation_error'))[:80],
            message=str(error.get('msg', 'Valor invalido.'))[:160],
        ).model_dump(mode='json')
        for error in exc.errors()
    ]
    return {'errors': issues}


def _request_route(request: Request) -> str:
    route = request.scope.get('route')
    return str(getattr(route, 'path', request.url.path))


def _log_error(
    request: Request,
    exc: Exception,
    *,
    error_code: str,
    status_code: int,
    retryable: bool,
    incident_id: str,
) -> None:
    token = incident_id_ctx.set(incident_id)
    try:
        level = logging.ERROR if status_code >= 500 else logging.WARNING
        logger.log(
            level,
            'api.request.error',
            exc_info=(type(exc), exc, exc.__traceback__) if status_code >= 500 else None,
            extra={
                'event': 'api.request.error',
                'method': request.method,
                'route': _request_route(request),
                'status_code': status_code,
                'error_code': error_code,
                'retryable': retryable,
            },
        )
    finally:
        incident_id_ctx.reset(token)


def _build_error_response(
    *,
    request: Request,
    code: ErrorCode | str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    exc: Exception | None = None,
    retryable: bool = False,
) -> JSONResponse:
    incident_id = uuid.uuid4().hex
    trace_id, span_id = current_trace_context()
    code_value = str(code)

    if exc is not None:
        if status_code >= 500:
            _record_exception_on_span(exc)
        _log_error(
            request,
            exc,
            error_code=code_value,
            status_code=status_code,
            retryable=retryable,
            incident_id=incident_id,
        )

    envelope = ErrorEnvelopeOut(
        error=ErrorBodyOut(
            code=code_value,
            message=message,
            retryable=retryable,
            details=_sanitize_public_details(details),
            diagnostics=ErrorDiagnosticsOut(
                timestamp=datetime.now(UTC),
                status_code=status_code,
                incident_id=incident_id,
                request_id=request_id_ctx.get() or None,
                trace_id=trace_id,
                span_id=span_id,
            ),
        )
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode='json'))


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
            retryable=exc.retryable,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            code=ErrorCode.VALIDATION_ERROR,
            message='Dados de entrada invalidos.',
            status_code=422,
            details=_validation_details(exc),
            exc=exc,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        messages = {
            401: 'Autenticacao necessaria.',
            403: 'Acesso negado.',
            404: 'Recurso nao encontrado.',
            405: 'Metodo nao permitido.',
        }
        return _build_error_response(
            request=request,
            code=ErrorCode.HTTP_ERROR,
            message=messages.get(exc.status_code, 'Nao foi possivel concluir a requisicao.'),
            status_code=exc.status_code,
            exc=exc,
        )

    @app.exception_handler(TransientIntegrationError)
    async def transient_integration_handler(
        request: Request,
        exc: TransientIntegrationError,
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            code=ErrorCode.INTEGRATION_TEMPORARY_FAILURE,
            message='Uma dependencia esta temporariamente indisponivel.',
            status_code=503,
            exc=exc,
            retryable=True,
        )

    @app.exception_handler(InfrastructureError)
    async def infrastructure_handler(
        request: Request,
        exc: InfrastructureError,
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            code=ErrorCode.INFRASTRUCTURE_FAILURE,
            message='Nao foi possivel concluir a operacao externa.',
            status_code=502,
            exc=exc,
            retryable=True,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return _build_error_response(
            request=request,
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message='Ocorreu um erro inesperado. Tente novamente mais tarde.',
            status_code=500,
            exc=exc,
            retryable=True,
        )
