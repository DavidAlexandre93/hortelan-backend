from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from app.api.contracts import (
    DependencyStatus,
    HealthOut,
    HealthStatus,
    LivenessOut,
    ReadinessOut,
    RootStatusOut,
)
from app.api.error_handlers import register_exception_handlers
from app.api.routes import router
from app.core.dependencies import get_container
from app.core.observability import (
    ObservabilityMiddleware,
    configure_logging,
    configure_telemetry,
    metrics_registry,
)
from app.core.settings import get_settings

settings = get_settings()
logger = configure_logging(settings)
VERCEL_ANALYTICS_SCRIPT = '<script defer src="/_vercel/insights/script.js"></script>'


def _inject_vercel_analytics(response: HTMLResponse) -> HTMLResponse:
    rendered_html = bytes(response.body).decode('utf-8')
    if VERCEL_ANALYTICS_SCRIPT in rendered_html:
        return response

    response.body = rendered_html.replace(
        '</head>',
        f'    {VERCEL_ANALYTICS_SCRIPT}\n  </head>',
    ).encode('utf-8')
    response.headers['content-length'] = str(len(response.body))
    return response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    container = get_container()
    try:
        await container.relational_repo.init_schema()
        logger.info('application.started', extra={'event': 'application.started'})
        yield
    finally:
        await container.close()
        logger.info('application.stopped', extra={'event': 'application.stopped'})


favicon_svg_path = Path(__file__).resolve().parent / 'static' / 'favicon.svg'

app = FastAPI(
    title=settings.app_name,
    description=(
        'API da plataforma Hortelan para integracao IoT, ingestao de telemetria, envio de '
        'comandos e rastreabilidade de cobertura estrategica do produto.'
    ),
    version=settings.app_version,
    contact={'name': 'Equipe Hortelan', 'email': 'tech@hortelan.local'},
    license_info={'name': 'MIT', 'url': 'https://opensource.org/licenses/MIT'},
    openapi_version='3.1.0',
    openapi_tags=[
        {'name': 'telemetria', 'description': 'Ingestao e consulta de medicoes dos sensores.'},
        {'name': 'comandos', 'description': 'Envio e consulta de comandos dos dispositivos.'},
        {'name': 'dispositivos', 'description': 'Estado consolidado por dispositivo.'},
        {'name': 'ledger', 'description': 'Trilha operacional e de auditoria.'},
        {
            'name': 'cobertura estrategica',
            'description': 'Cobertura de requisitos e prontidao dos modulos.',
        },
        {'name': 'requirements', 'description': 'Detalhes dos requisitos do catalogo.'},
        {'name': 'saude', 'description': 'Liveness, readiness e estado da aplicacao.'},
    ],
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(ObservabilityMiddleware, logger=logger, settings=settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)
app.include_router(router)
register_exception_handlers(app)
configure_telemetry(app, settings)


@app.get('/docs', include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url or '/openapi.json',
        title=f'{app.title} - Swagger UI',
        swagger_favicon_url='/favicon.svg',
    )
    return _inject_vercel_analytics(response)


@app.get('/redoc', include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    response = get_redoc_html(
        openapi_url=app.openapi_url or '/openapi.json',
        title=f'{app.title} - ReDoc',
        redoc_favicon_url='/favicon.svg',
    )
    return _inject_vercel_analytics(response)


@app.get('/favicon.svg', include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(favicon_svg_path, media_type='image/svg+xml')


@app.get('/favicon.ico', include_in_schema=False)
async def favicon_ico() -> FileResponse:
    return FileResponse(favicon_svg_path, media_type='image/svg+xml')


@app.get('/', response_model=RootStatusOut, include_in_schema=False)
async def root_status() -> RootStatusOut:
    return RootStatusOut(message='Service available', version=settings.app_version)


@app.get('/health', response_model=HealthOut, tags=['saude'], summary='Estado da API')
async def health() -> HealthOut:
    return HealthOut(
        status=HealthStatus.OK,
        environment=settings.app_env.value,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


@app.get('/health/live', response_model=LivenessOut, tags=['saude'])
async def health_live() -> LivenessOut:
    return LivenessOut(status=HealthStatus.ALIVE, timestamp=datetime.now(UTC))


@app.get(
    '/health/ready',
    response_model=ReadinessOut,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {'model': ReadinessOut}},
    tags=['saude'],
)
async def health_ready(response: Response) -> ReadinessOut:
    checks = {'database': DependencyStatus.OK}
    readiness_status = HealthStatus.READY
    try:
        async with asyncio.timeout(settings.health_check_timeout_seconds):
            await get_container().relational_repo.ping()
    except Exception:
        checks['database'] = DependencyStatus.ERROR
        readiness_status = HealthStatus.DEGRADED
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.exception(
            'health.readiness.failed',
            extra={'event': 'health.readiness.failed', 'dependency': 'database'},
        )

    return ReadinessOut(
        status=readiness_status,
        checks=checks,
        environment=settings.app_env.value,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


@app.get('/metrics', include_in_schema=False)
async def metrics() -> PlainTextResponse:
    if not settings.enable_metrics:
        return PlainTextResponse('metrics disabled\n', status_code=status.HTTP_404_NOT_FOUND)
    return PlainTextResponse(
        metrics_registry.render_prometheus(),
        media_type='text/plain; version=0.0.4',
    )
