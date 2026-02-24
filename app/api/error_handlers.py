import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, format_span_id, format_trace_id

logger = logging.getLogger(__name__)


def _current_trace_context() -> dict[str, str | None]:
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if not span_context or not span_context.is_valid:
        return {'trace_id': None, 'span_id': None}

    return {
        'trace_id': format_trace_id(span_context.trace_id),
        'span_id': format_span_id(span_context.span_id),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_context = _current_trace_context()

        span = trace.get_current_span()
        if span:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))

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
            'detail': 'Erro interno inesperado.',
            'error_type': type(exc).__name__,
            'path': request.url.path,
            'method': request.method,
            'trace_id': trace_context['trace_id'],
            'span_id': trace_context['span_id'],
        }
        return JSONResponse(status_code=500, content=body)
