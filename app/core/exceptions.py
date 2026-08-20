from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    UNAUTHORIZED = 'UNAUTHORIZED'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    HTTP_ERROR = 'HTTP_ERROR'
    IDEMPOTENCY_KEY_REQUIRED = 'IDEMPOTENCY_KEY_REQUIRED'
    IDEMPOTENCY_CONFLICT = 'IDEMPOTENCY_CONFLICT'
    IDEMPOTENCY_IN_PROGRESS = 'IDEMPOTENCY_IN_PROGRESS'
    INTEGRATION_TEMPORARY_FAILURE = 'INTEGRATION_TEMPORARY_FAILURE'
    INFRASTRUCTURE_FAILURE = 'INFRASTRUCTURE_FAILURE'
    INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR'
    RATE_LIMITED = 'RATE_LIMITED'


class InfrastructureError(Exception):
    """Falha de infraestrutura que impede a operacao principal."""


class TransientIntegrationError(InfrastructureError):
    """Falha transitoria em integracao externa, passivel de degradacao controlada."""


class ApiError(Exception):
    """Erro esperado de API contendo apenas mensagem e detalhes seguros para o cliente."""

    def __init__(
        self,
        message: str,
        code: ErrorCode | str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = str(code)
        self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable


class UnauthorizedError(ApiError):
    def __init__(self, message: str = 'Nao autorizado') -> None:
        super().__init__(message=message, code=ErrorCode.UNAUTHORIZED, status_code=401)


class IdempotencyKeyRequiredError(ApiError):
    def __init__(self) -> None:
        super().__init__(
            message='Informe uma Idempotency-Key valida para esta operacao.',
            code=ErrorCode.IDEMPOTENCY_KEY_REQUIRED,
            status_code=400,
        )


class IdempotencyConflictError(ApiError):
    def __init__(self) -> None:
        super().__init__(
            message='A Idempotency-Key ja foi usada para outra operacao.',
            code=ErrorCode.IDEMPOTENCY_CONFLICT,
            status_code=409,
        )


class IdempotencyInProgressError(ApiError):
    def __init__(self) -> None:
        super().__init__(
            message='O resultado desta operacao ainda e incerto. Tente consultar novamente mais tarde.',
            code=ErrorCode.IDEMPOTENCY_IN_PROGRESS,
            status_code=409,
            retryable=True,
        )
