from fastapi import Header

from app.core.exceptions import UnauthorizedError
from app.core.settings import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()

    if settings.api_key:
        if x_api_key != settings.api_key:
            raise UnauthorizedError('API key inválida ou ausente')
        return

    if settings.app_env.lower() == 'production' and settings.enforce_api_key_in_production:
        raise UnauthorizedError('API key obrigatória em produção')

