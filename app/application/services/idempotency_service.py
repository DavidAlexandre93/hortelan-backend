from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.exceptions import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyKeyRequiredError,
)
from app.domain.entities.models import IdempotencyRecord, IdempotencyState
from app.domain.ports.interfaces import IdempotencyRepositoryPort

IDEMPOTENCY_KEY_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$')


class IdempotencyService:
    def __init__(self, repository: IdempotencyRepositoryPort) -> None:
        self.repository = repository

    async def execute(
        self,
        *,
        key: str | None,
        operation: str,
        payload: dict[str, Any],
        action: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        if key is None or not IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
            raise IdempotencyKeyRequiredError()

        fingerprint = self._fingerprint(operation, payload)
        created, record = await self.repository.reserve(
            IdempotencyRecord(
                key=key,
                operation=operation,
                fingerprint=fingerprint,
                state=IdempotencyState.PROCESSING,
            )
        )

        if not created:
            if record.operation != operation or record.fingerprint != fingerprint:
                raise IdempotencyConflictError()
            if record.state is IdempotencyState.COMPLETED and record.response is not None:
                return {**record.response, 'idempotency_key': key, 'replayed': True}
            raise IdempotencyInProgressError()

        try:
            response = await action()
        except Exception:
            await self.repository.mark_unknown(key)
            raise

        result = {**response, 'idempotency_key': key, 'replayed': False}
        await self.repository.complete(key, result)
        return result

    @staticmethod
    def _fingerprint(operation: str, payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            {'operation': operation, 'payload': payload},
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
