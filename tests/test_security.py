import asyncio

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import require_api_key
from app.core.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_require_api_key_allows_when_not_configured(monkeypatch):
    monkeypatch.delenv('API_KEY', raising=False)

    asyncio.run(require_api_key(None))


def test_require_api_key_blocks_invalid_key(monkeypatch):
    monkeypatch.setenv('API_KEY', 'super-secret')

    with pytest.raises(UnauthorizedError):
        asyncio.run(require_api_key('invalid'))


def test_require_api_key_allows_valid_key(monkeypatch):
    monkeypatch.setenv('API_KEY', 'super-secret')

    asyncio.run(require_api_key('super-secret'))
