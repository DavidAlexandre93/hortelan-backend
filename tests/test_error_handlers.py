import asyncio

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.api.error_handlers import register_exception_handlers
from app.core.exceptions import ApiError


def _build_request(path: str, method: str = 'GET') -> Request:
    scope = {
        'type': 'http',
        'http_version': '1.1',
        'method': method,
        'path': path,
        'raw_path': path.encode('utf-8'),
        'scheme': 'http',
        'query_string': b'',
        'headers': [],
        'client': ('127.0.0.1', 12345),
        'server': ('testserver', 80),
    }
    return Request(scope)


def _build_handlers():
    app = FastAPI()
    register_exception_handlers(app)
    return app.exception_handlers


def test_api_error_returns_diagnostic_payload():
    handlers = _build_handlers()
    request = _build_request('/domain-error')

    response = asyncio.run(
        handlers[ApiError](
            request,
            ApiError(message='Falha de domínio', code='DOMAIN_ERROR', status_code=409, details={'entity': 'order'}),
        )
    )

    assert response.status_code == 409
    payload = response.body.decode('utf-8')
    assert 'DOMAIN_ERROR' in payload
    assert '"status_code":409' in payload
    assert '"path":"/domain-error"' in payload


def test_validation_error_returns_structured_details():
    handlers = _build_handlers()
    request = _build_request('/items/not-an-int')
    validation_error = RequestValidationError(
        [
            {
                'type': 'int_parsing',
                'loc': ('path', 'item_id'),
                'msg': 'Input should be a valid integer',
                'input': 'not-an-int',
            }
        ]
    )

    response = asyncio.run(handlers[RequestValidationError](request, validation_error))

    assert response.status_code == 422
    payload = response.body.decode('utf-8')
    assert 'VALIDATION_ERROR' in payload
    assert 'int_parsing' in payload


def test_unhandled_exception_returns_internal_error_payload():
    handlers = _build_handlers()
    request = _build_request('/boom')

    response = asyncio.run(handlers[Exception](request, RuntimeError('kaboom')))

    assert response.status_code == 500
    payload = response.body.decode('utf-8')
    assert 'INTERNAL_SERVER_ERROR' in payload
    assert 'RuntimeError' in payload
    assert 'traceback' in payload
