class InfrastructureError(Exception):
    """Falha de infraestrutura que impede a operação principal."""


class TransientIntegrationError(InfrastructureError):
    """Falha transitória em integração externa (passível de degradação controlada)."""
