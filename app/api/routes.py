from datetime import datetime
from re import sub

from fastapi import APIRouter, Query

from app.api.schemas import (
    AckResponse,
    DeviceSnapshotOut,
    IrrigationCommandIn,
    LedgerRecordIn,
    RequirementCoverageOut,
    RequirementDetailOut,
    TelemetryIn,
    TelemetryOut,
)
from app.core.dependencies import container
from app.domain.entities.models import IrrigationCommand, LedgerRecord, TelemetryReading

router = APIRouter(prefix='/api/v1')


REQUIREMENT_CATALOG: list[tuple[str, str]] = [
    ('1.1', 'Cadastro de usuário'),
    ('1.2', 'Login'),
    ('1.3', 'Recuperação de senha'),
    ('1.4', 'Autenticação avançada'),
    ('1.5', 'Perfil do usuário'),
    ('1.6', 'Gestão da conta'),
    ('2.1', 'Cadastro de horta'),
    ('2.2', 'Estrutura por áreas/setores'),
    ('2.3', 'Cadastro de recipientes/unidades'),
    ('2.4', 'Mapa visual da horta'),
    ('3.1', 'Cadastro de planta/cultivo'),
    ('3.2', 'Biblioteca de espécies'),
    ('3.3', 'Planejamento de plantio'),
    ('3.4', 'Histórico da planta'),
    ('3.5', 'Status de saúde da planta'),
    ('4.1', 'Cadastro de dispositivos IoT'),
    ('4.2', 'Cadastro de sensores'),
    ('4.3', 'Cadastro de atuadores'),
    ('4.4', 'Estado e conectividade do dispositivo'),
    ('4.5', 'Telemetria em tempo real'),
    ('4.6', 'Histórico de telemetria'),
    ('5.1', 'Dashboard geral'),
    ('5.2', 'Dashboard por horta'),
    ('5.3', 'Dashboard por planta'),
    ('5.4', 'Alertas visuais'),
    ('5.5', 'Painel operacional em tempo real'),
    ('6.1', 'Regras por condição'),
    ('6.2', 'Regras por agenda/horário'),
    ('6.3', 'Regras híbridas'),
    ('6.4', 'Templates de automação'),
    ('6.5', 'Simulação/teste de regra'),
    ('6.6', 'Logs de automação'),
    ('6.7', 'Modo manual / override'),
    ('7.1', 'Agenda de tarefas'),
    ('7.2', 'Criação de tarefas personalizadas'),
    ('7.3', 'Lembretes e vencimentos'),
    ('7.4', 'Execução e evidências'),
    ('7.5', 'Rotinas automáticas sugeridas'),
    ('8.1', 'Integração com clima'),
    ('8.2', 'Impacto no cultivo'),
    ('8.3', 'Regras usando clima externo'),
    ('8.4', 'Histórico climático correlacionado'),
    ('9.1', 'Recomendação de cuidados'),
    ('9.2', 'Diagnóstico por regras'),
    ('9.3', 'Diagnóstico por foto'),
    ('9.4', 'Identificação de espécie por foto'),
    ('9.5', 'Assistente virtual Hortelan'),
    ('9.6', 'Score de saúde da horta'),
    ('10.1', 'Central de alertas'),
    ('10.2', 'Tipos de alerta'),
    ('10.3', 'Notificações'),
    ('10.4', 'Política de notificações'),
    ('10.5', 'Gestão de incidentes'),
    ('11.1', 'Relatórios operacionais'),
    ('11.2', 'Relatórios de cultivo'),
    ('11.3', 'Relatórios de manutenção'),
    ('11.4', 'Exportação de dados'),
    ('11.5', 'Histórico unificado'),
    ('12.1', 'Perfil público/comunidade'),
    ('12.2', 'Publicações'),
    ('12.3', 'Interação social'),
    ('12.4', 'Perguntas e respostas'),
    ('12.5', 'Feed da comunidade'),
    ('12.6', 'Sistema de reputação'),
    ('12.7', 'Moderação'),
    ('13.1', 'Templates de cultivo'),
    ('13.2', 'Templates de automação compartilháveis'),
    ('13.3', 'Receitas de solução de problemas'),
    ('13.4', 'Avaliação de templates'),
    ('14.1', 'Catálogo de produtos'),
    ('14.2', 'Busca e filtros'),
    ('14.3', 'Página de produto'),
    ('14.4', 'Carrinho'),
    ('14.5', 'Checkout'),
    ('14.6', 'Área do cliente (pedidos)'),
    ('14.7', 'Recomendações de compra contextuais'),
    ('15.1', 'Programa de pontos'),
    ('15.2', 'Badges e conquistas'),
    ('15.3', 'Cupons'),
    ('15.4', 'Desafios'),
    ('16.1', 'Planos de uso'),
    ('16.2', 'Gestão da assinatura'),
    ('16.3', 'Controle de limites por plano'),
    ('17.1', 'Compartilhar horta'),
    ('17.2', 'Papéis e permissões (RBAC)'),
    ('17.3', 'Auditoria de ações'),
    ('18.1', 'Gestão de usuários (admin)'),
    ('18.2', 'Gestão de dispositivos e catálogo IoT'),
    ('18.3', 'Gestão de conteúdo (CMS leve)'),
    ('18.4', 'Gestão da comunidade'),
    ('18.5', 'Gestão da loja'),
    ('18.6', 'Gestão de assinaturas e faturamento'),
    ('18.7', 'Observabilidade da plataforma'),
    ('19.1', 'Central de ajuda'),
    ('19.2', 'Abertura de chamado'),
    ('19.3', 'Acompanhamento de chamados'),
    ('19.4', 'Suporte contextual'),
    ('20.1', 'Onboarding guiado'),
    ('20.2', 'Checklist inicial'),
    ('20.3', 'Demo / modo simulado'),
    ('20.4', 'Educação contextual'),
    ('21.1', 'Segurança de aplicação'),
    ('21.2', 'Privacidade e consentimento'),
    ('21.3', 'LGPD'),
    ('21.4', 'Segurança de dispositivos'),
    ('22.1', 'Preferências da plataforma'),
    ('22.2', 'Preferências de cultivo'),
    ('22.3', 'Preferências de notificação'),
    ('23.1', 'Integrações de clima e geodados'),
    ('23.2', 'Integrações de pagamento'),
    ('23.3', 'Integrações logísticas'),
    ('23.4', 'Integrações de mensageria'),
    ('23.5', 'Integrações IoT/ecossistema'),
    ('24.1', 'Gestão de múltiplas unidades'),
    ('24.2', 'Perfis institucionais'),
    ('24.3', 'Relatórios institucionais'),
    ('24.4', 'Módulo educacional'),
    ('25.1', 'Logs e auditoria'),
    ('25.2', 'Observabilidade'),
    ('25.3', 'Feature flags'),
    ('25.4', 'Backup e recuperação'),
]

IMPLEMENTED_REQUIREMENTS = {'4.5', '4.6', '4.1', '4.4', '25.1'}


def _slugify_requirement(requirement_id: str, title: str) -> str:
    normalized = sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    normalized_id = requirement_id.replace('.', '-')
    return f'{normalized_id}-{normalized}'


def _build_requirement_detail(requirement_id: str, title: str) -> RequirementDetailOut:
    slug = _slugify_requirement(requirement_id, title)
    implemented = requirement_id in IMPLEMENTED_REQUIREMENTS
    note = (
        'Requisito já possui endpoints funcionais no backend atual.'
        if implemented
        else 'Endpoint criado como marcador de cobertura para evolução incremental deste requisito.'
    )
    return RequirementDetailOut(
        requirement_id=requirement_id,
        title=title,
        endpoint=f'/api/v1/requirements/{slug}',
        implemented=implemented,
        notes=note,
    )


@router.post('/telemetry', response_model=AckResponse)
async def ingest_telemetry(payload: TelemetryIn) -> AckResponse:
    await container.ingest_telemetry_use_case.execute(
        TelemetryReading(
            device_id=payload.device_id,
            moisture=payload.moisture,
            temperature=payload.temperature,
            ph=payload.ph,
            metadata=payload.metadata,
        )
    )
    return AckResponse(status='telemetry_ingested', timestamp=datetime.utcnow())


@router.get('/telemetry', response_model=list[TelemetryOut])
async def list_telemetry(
    limit: int = Query(default=20, ge=1, le=200),
    device_id: str | None = Query(default=None),
) -> list[TelemetryOut]:
    items = await container.relational_repo.list_recent(limit=limit, device_id=device_id)
    return [
        TelemetryOut(
            device_id=item.device_id,
            moisture=item.moisture,
            temperature=item.temperature,
            ph=item.ph,
            captured_at=item.captured_at,
            metadata=item.metadata,
        )
        for item in items
    ]


@router.get('/telemetry/latest/{device_id}', response_model=TelemetryOut | None)
async def latest_telemetry(device_id: str) -> TelemetryOut | None:
    cached = await container.cache.get(f'telemetry:{device_id}')
    if not cached:
        return None

    return TelemetryOut(
        device_id=cached['device_id'],
        moisture=cached['moisture'],
        temperature=cached['temperature'],
        ph=cached['ph'],
        captured_at=datetime.fromisoformat(cached['captured_at']),
        metadata=cached.get('metadata', {}),
    )


@router.post('/commands', response_model=AckResponse)
async def dispatch_command(payload: IrrigationCommandIn) -> AckResponse:
    await container.dispatch_irrigation_command_use_case.execute(
        IrrigationCommand(
            device_id=payload.device_id,
            action=payload.action,
            duration_seconds=payload.duration_seconds,
        )
    )
    return AckResponse(status='command_dispatched', timestamp=datetime.utcnow())


@router.get('/commands/latest/{device_id}', response_model=dict)
async def latest_command(device_id: str) -> dict:
    return await container.cache.get(f'command:{device_id}') or {}


@router.post('/ledger', response_model=AckResponse)
async def register_ledger(payload: LedgerRecordIn) -> AckResponse:
    await container.register_ledger_record_use_case.execute(
        LedgerRecord(record_id=payload.record_id, payload=payload.payload)
    )
    return AckResponse(status='ledger_registered', timestamp=datetime.utcnow())


@router.get('/devices/{device_id}/snapshot', response_model=DeviceSnapshotOut)
async def get_device_snapshot(device_id: str) -> DeviceSnapshotOut:
    telemetry = await container.cache.get(f'telemetry:{device_id}')
    command = await container.cache.get(f'command:{device_id}')
    return DeviceSnapshotOut(device_id=device_id, telemetry=telemetry, command=command)


@router.get('/requirements', response_model=list[RequirementCoverageOut])
async def list_requirement_coverage() -> list[RequirementCoverageOut]:
    return [
        RequirementCoverageOut(
            requirement_id=requirement_id,
            title=title,
            endpoint=f'/api/v1/requirements/{_slugify_requirement(requirement_id, title)}',
            implemented=requirement_id in IMPLEMENTED_REQUIREMENTS,
        )
        for requirement_id, title in REQUIREMENT_CATALOG
    ]


def _requirement_endpoint(requirement_id: str, title: str):
    async def _handler() -> RequirementDetailOut:
        return _build_requirement_detail(requirement_id, title)

    _handler.__name__ = f"requirement_{requirement_id.replace('.', '_')}"
    return _handler


for _requirement_id, _title in REQUIREMENT_CATALOG:
    _slug = _slugify_requirement(_requirement_id, _title)
    router.add_api_route(
        f'/requirements/{_slug}',
        _requirement_endpoint(_requirement_id, _title),
        methods=['GET'],
        response_model=RequirementDetailOut,
        tags=['requirements'],
        summary=f'Cobertura do requisito {_requirement_id}',
    )
