class InfrastructureError(Exception):
    """Falha de infraestrutura que impede a operação principal."""


class TransientIntegrationError(InfrastructureError):
    """Falha transitória em integração externa (passível de degradação controlada)."""


class ApiError(Exception):
    """Erro de API com status e código padronizados."""

    def __init__(self, message: str, code: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class UnauthorizedError(ApiError):
    def __init__(self, message: str = 'Não autorizado') -> None:
        super().__init__(message=message, code='UNAUTHORIZED', status_code=401)
