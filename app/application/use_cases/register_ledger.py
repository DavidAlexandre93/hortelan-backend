"""Compat: mantenha import legado.

Novo caminho recomendado:
app.application.use_cases.governance.register_ledger_record_use_case.RegisterLedgerRecordUseCase
"""

from app.application.use_cases.governance.register_ledger_record_use_case import RegisterLedgerRecordUseCase

__all__ = ['RegisterLedgerRecordUseCase']
