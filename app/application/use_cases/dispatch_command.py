"""Compat: mantenha import legado.

Novo caminho recomendado:
app.application.use_cases.iot.dispatch_irrigation_command_use_case.DispatchIrrigationCommandUseCase
"""

from app.application.use_cases.iot.dispatch_irrigation_command_use_case import DispatchIrrigationCommandUseCase

__all__ = ['DispatchIrrigationCommandUseCase']
