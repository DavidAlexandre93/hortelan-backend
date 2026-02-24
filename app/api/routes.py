from datetime import datetime
from re import sub

from fastapi import APIRouter, Query

from app.api.schemas import (
    AckResponse,
    DeviceSnapshotOut,
    IrrigationCommandIn,
    LedgerRecordIn,
    ProductModuleCoverageOut,
    ProductReadinessReportOut,
    RequirementCoverageOut,
    RequirementDetailOut,
    StrategicCoverageReportOut,
    StrategicFeatureCoverageOut,
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

PRODUCT_MODULES: list[dict[str, object]] = [
    {
        'slug': 'cadastro-login',
        'title': 'Cadastro/login',
        'stage': 'MVP',
        'status': 'não atende',
        'implemented': False,
        'existing_endpoints': [],
        'notes': 'Não há endpoints dedicados de autenticação/conta no backend atual.',
    },
    {
        'slug': 'cadastro-horta-area-planta',
        'title': 'Cadastro de horta/área/planta',
        'stage': 'MVP',
        'status': 'não atende',
        'implemented': False,
        'existing_endpoints': [],
        'notes': 'Existe apenas catálogo de requisitos; faltam recursos CRUD de domínio de cultivo.',
    },
    {
        'slug': 'dashboard-basico',
        'title': 'Dashboard básico',
        'stage': 'MVP',
        'status': 'atende parcialmente',
        'implemented': False,
        'existing_endpoints': ['/api/v1/devices/{device_id}/snapshot', '/api/v1/telemetry/latest/{device_id}'],
        'notes': 'Há dados de suporte ao dashboard, mas sem endpoints consolidados por negócio.',
    },
    {
        'slug': 'integracao-iot-basica',
        'title': 'Integração IoT básica (sensores principais)',
        'stage': 'MVP',
        'status': 'atende',
        'implemented': True,
        'existing_endpoints': ['/api/v1/telemetry', '/api/v1/commands', '/api/v1/devices/{device_id}/snapshot'],
        'notes': 'Fluxo principal de telemetria/comando está funcional no backend.',
    },
    {
        'slug': 'alertas-basicos',
        'title': 'Alertas básicos',
        'stage': 'MVP',
        'status': 'não atende',
        'implemented': False,
        'existing_endpoints': [],
        'notes': 'Não há pipeline/endpoints de alertas ativos.',
    },
    {
        'slug': 'tarefas-lembretes',
        'title': 'Tarefas e lembretes',
        'stage': 'MVP',
        'status': 'não atende',
        'implemented': False,
        'existing_endpoints': [],
        'notes': 'Sem módulo de agenda ou rotinas de tarefas.',
    },
    {
        'slug': 'automacao-simples',
        'title': 'Automação simples (if/then)',
        'stage': 'MVP',
        'status': 'não atende',
        'implemented': False,
        'existing_endpoints': [],
        'notes': 'Comandos manuais existem, porém sem mecanismo de regras if/then exposto.',
    },
    {
        'slug': 'historico-graficos-basicos',
        'title': 'Histórico e gráficos básicos',
        'stage': 'MVP',
        'status': 'atende parcialmente',
        'implemented': False,
        'existing_endpoints': ['/api/v1/telemetry'],
        'notes': 'Histórico bruto existe; agregações para gráficos ainda não.',
    },
    {'slug': 'comunidade', 'title': 'Comunidade', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem endpoints sociais/comunidade.'},
    {'slug': 'templates-cultivo-automacao', 'title': 'Templates de cultivo/automação', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem catálogo de templates aplicáveis.'},
    {'slug': 'relatorios-avancados', 'title': 'Relatórios avançados', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem relatórios especializados/exportações avançadas.'},
    {'slug': 'clima-regras-clima', 'title': 'Clima e regras com clima', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Integração meteorológica e regras climáticas não implementadas.'},
    {'slug': 'multiusuario-permissoes', 'title': 'Multiusuário/permissões', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem RBAC e compartilhamento de hortas.'},
    {'slug': 'notificacoes-avancadas', 'title': 'Notificações avançadas', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Não existe central/política de notificações avançadas.'},
    {'slug': 'backoffice-robusto', 'title': 'Backoffice robusto', 'stage': 'V2', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem APIs administrativas dedicadas.'},
    {'slug': 'diagnostico-por-foto', 'title': 'Diagnóstico por foto', 'stage': 'V3', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Não há inferência/computer vision integrado.'},
    {'slug': 'assistente-inteligente', 'title': 'Assistente inteligente', 'stage': 'V3', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem endpoint de assistente conversacional/recomendações inteligentes.'},
    {'slug': 'marketplace-completo', 'title': 'Marketplace completo', 'stage': 'V3', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem catálogo/carrinho/checkout no backend.'},
    {'slug': 'recompensas-gamificacao-avancadas', 'title': 'Recompensas/gamificação avançadas', 'stage': 'V3', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem regras de pontos, badges e desafios.'},
    {'slug': 'b2b-b2g', 'title': 'B2B/B2G', 'stage': 'V3', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Sem módulos corporativos/institucionais.'},
    {'slug': 'modo-local-offline', 'title': 'Modo local/offline para confiança operacional (se aplicável ao hardware)', 'stage': 'V3', 'status': 'não atende', 'implemented': False, 'existing_endpoints': [], 'notes': 'Não há estratégia offline exposta via API para operação desconectada.'},
]

PRODUCT_MODULE_INDEX = {item['slug']: item for item in PRODUCT_MODULES}

STRATEGIC_COVERAGE_MATRIX: list[tuple[str, str, str]] = [
    (
        'Cadastro e gestão de hortas/plantas',
        'Não atende ainda',
        'Está catalogado como requisito (2.1 e 3.1), mas fora do conjunto marcado como implementado.',
    ),
    (
        'Integração com sensores e dispositivos IoT',
        'Atende parcialmente',
        'Existem endpoints de telemetria/comandos e snapshot de dispositivo; requisitos 4.1, 4.4, 4.5 e 4.6 estão marcados como implementados.',
    ),
    (
        'Dashboard de monitoramento',
        'Não atende ainda (backend dedicado)',
        'Requisitos de dashboard (5.x) existem no catálogo, mas não estão marcados como implementados.',
    ),
    (
        'Automação por regras',
        'Não atende ainda',
        'Requisitos de automação (6.x) estão no catálogo sem marcação de implementação.',
    ),
    (
        'Alertas e notificações',
        'Não atende ainda',
        'Requisitos (10.x) aparecem no catálogo, sem implementação marcada.',
    ),
    (
        'Agenda de tarefas de cultivo',
        'Não atende ainda',
        'Requisitos (7.x) presentes no catálogo, não implementados.',
    ),
    (
        'Recomendações inteligentes (e diagnóstico por foto em fase avançada)',
        'Não atende ainda',
        'Requisitos (9.x) existem no catálogo, mas sem implementação funcional marcada.',
    ),
    (
        'Comunidade com compartilhamento de experiências',
        'Não atende ainda',
        'Requisitos de comunidade (12.x) no catálogo sem implementação.',
    ),
    (
        'Templates/receitas de cultivo e automação',
        'Não atende ainda',
        'Requisitos (13.x) no catálogo sem implementação.',
    ),
    (
        'Marketplace integrado com recomendações contextuais',
        'Não atende ainda',
        'Requisitos de loja/marketplace (14.x) no catálogo sem implementação.',
    ),
    (
        'Gamificação/recompensas',
        'Não atende ainda',
        'Requisitos (15.x) no catálogo sem implementação.',
    ),
    (
        'Backoffice/admin + suporte + LGPD',
        'Atende parcialmente (escopo restrito)',
        'Só há marcação para auditoria/logs (25.1) e catálogo de requisitos de admin/suporte/LGPD (18.x, 19.x, 21.3), ainda não marcados como implementados.',
    ),
]

STRATEGIC_NEXT_STEPS = [
    'Modelagem de domínio de horta/planta/tarefas para habilitar cadastro e agenda (2.x, 3.x, 7.x).',
    'Motor de regras e alertas (6.x + 10.x), reaproveitando pipeline já existente de telemetria/comandos.',
    'Camada de recomendações inicialmente baseada em regras (9.1/9.2), deixando visão computacional (9.3/9.4) como etapa posterior.',
    'Módulos de produto (12.x, 13.x, 14.x, 15.x) com rollout incremental por domínio.',
    'Backoffice/LGPD/suporte (18.x, 19.x, 21.x) com trilha de auditoria e consentimento evoluindo de 25.1.',
]


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


def _build_product_module_detail(module: dict[str, object]) -> ProductModuleCoverageOut:
    slug = str(module['slug'])
    return ProductModuleCoverageOut(
        slug=slug,
        title=str(module['title']),
        stage=str(module['stage']),
        status=str(module['status']),
        implemented=bool(module['implemented']),
        existing_endpoints=list(module['existing_endpoints']),
        endpoint=f'/api/v1/product/modules/{slug}',
        notes=str(module['notes']),
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


@router.get('/strategic/coverage', response_model=StrategicCoverageReportOut)
async def strategic_coverage_report() -> StrategicCoverageReportOut:
    return StrategicCoverageReportOut(
        overall_result=(
            'O backend atual não atende integralmente ao núcleo estratégico completo. '
            'Ele está mais maduro no eixo de IoT/telemetria/comandos, com endpoints e casos de uso funcionando, '
            'e tem um catálogo de requisitos que já sinaliza cobertura parcial. '
            'Porém, a maioria dos módulos estratégicos de produto (comunidade, marketplace, gamificação, agenda, '
            'recomendações e backoffice completo) ainda está em fase de estruturação.'
        ),
        matrix=[
            StrategicFeatureCoverageOut(feature=feature, status=status, evidence=evidence)
            for feature, status, evidence in STRATEGIC_COVERAGE_MATRIX
        ],
        next_steps=STRATEGIC_NEXT_STEPS,
    )


@router.get('/product/readiness', response_model=ProductReadinessReportOut)
async def product_readiness_report() -> ProductReadinessReportOut:
    implemented_count = len([module for module in PRODUCT_MODULES if module['implemented']])
    total = len(PRODUCT_MODULES)
    return ProductReadinessReportOut(
        summary=(
            f'Cobertura validada para {total} módulos estratégicos. '
            f'{implemented_count} atendidos, {total - implemented_count} pendentes ou parciais.'
        ),
        modules=[_build_product_module_detail(module) for module in PRODUCT_MODULES],
    )


@router.get('/product/modules/{module_slug}', response_model=ProductModuleCoverageOut)
async def product_module_detail(module_slug: str) -> ProductModuleCoverageOut:
    module = PRODUCT_MODULE_INDEX.get(module_slug)
    if not module:
        return ProductModuleCoverageOut(
            slug=module_slug,
            title='Módulo não catalogado',
            stage='N/A',
            status='não catalogado',
            implemented=False,
            existing_endpoints=[],
            endpoint=f'/api/v1/product/modules/{module_slug}',
            notes='Slug informado não existe no catálogo de módulos estratégicos.',
        )
    return _build_product_module_detail(module)


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
