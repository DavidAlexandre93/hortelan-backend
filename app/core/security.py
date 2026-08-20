from hmac import compare_digest
from typing import Annotated

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.exceptions import UnauthorizedError
from app.core.settings import get_settings

api_key_header = APIKeyHeader(
    name='X-API-Key',
    scheme_name='HortelanApiKey',
    description='Chave da API configurada pelo ambiente de execucao.',
    auto_error=False,
)


async def require_api_key(
    x_api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> None:
    settings = get_settings()
    expected = settings.api_key.get_secret_value()

    if expected and (x_api_key is None or not compare_digest(x_api_key, expected)):
        raise UnauthorizedError('API key invalida ou ausente')
