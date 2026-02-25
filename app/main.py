from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from sqlalchemy import text

from app.api.error_handlers import register_exception_handlers
from app.api.routes import router
from app.core.dependencies import get_container
from app.core.observability import configure_telemetry
from app.core.observability import ObservabilityMiddleware, configure_logging, metrics_registry
from app.core.settings import get_settings

settings = get_settings()
logger = configure_logging(settings.log_level)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    container = get_container()
    await container.relational_repo.init_schema()
    logger.info('application_started')
    yield
    await container.telemetry_publisher.close()
    logger.info('application_stopped')


favicon_svg_path = Path(__file__).resolve().parent / 'static' / 'favicon.svg'

app = FastAPI(
    title=settings.app_name,
    description=(
        'API da plataforma Hortelan para integração IoT, ingestão de telemetria, envio de comandos '
        'e rastreabilidade de cobertura estratégica do produto.'
    ),
    version='1.0.0',
    contact={
        'name': 'Equipe Hortelan',
        'email': 'tech@hortelan.local',
    },
    license_info={
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT',
    },
    openapi_tags=[
        {'name': 'telemetria', 'description': 'Operações para ingestão e consulta de medições de sensores.'},
        {'name': 'comandos', 'description': 'Envio e consulta de comandos para atuadores/dispositivos.'},
        {'name': 'dispositivos', 'description': 'Visão consolidada de estado por dispositivo.'},
        {'name': 'ledger', 'description': 'Registro de eventos de auditoria e trilha operacional.'},
        {
            'name': 'cobertura estratégica',
            'description': 'Endpoints analíticos de cobertura de requisitos e prontidão de módulos estratégicos.',
        },
        {'name': 'requirements', 'description': 'Detalhamento individual de requisitos do catálogo.'},
    ],
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(ObservabilityMiddleware, logger=logger)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(router)
register_exception_handlers(app)
configure_telemetry(app, settings)


@app.get('/docs', include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f'{app.title} - Swagger UI',
        swagger_favicon_url='/favicon.svg',
    )


@app.get('/redoc', include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f'{app.title} - ReDoc',
        redoc_favicon_url='/favicon.svg',
    )


@app.get('/favicon.svg', include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(favicon_svg_path, media_type='image/svg+xml')


@app.get('/favicon.ico', include_in_schema=False)
async def favicon_ico() -> FileResponse:
    return FileResponse(favicon_svg_path, media_type='image/svg+xml')


@app.get(
    '/health',
    tags=['telemetria'],
    summary='Healthcheck da API',
    description='Endpoint de verificação rápida de disponibilidade da API e ambiente ativo.',
)
async def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.app_env}


@app.get('/health/live')
async def health_live() -> dict[str, str]:
    return {'status': 'alive'}


@app.get('/health/ready')
async def health_ready() -> dict[str, object]:
    checks: dict[str, str] = {'database': 'ok'}
    status = 'ready'
    try:
        container = get_container()
        async with container.relational_repo.engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
    except Exception:
        checks['database'] = 'error'
        status = 'degraded'

    return {'status': status, 'checks': checks, 'environment': settings.app_env}


@app.get('/metrics', include_in_schema=False)
async def metrics() -> PlainTextResponse:
    if not settings.enable_metrics:
        return PlainTextResponse('metrics disabled\n', status_code=404)
    return PlainTextResponse(metrics_registry.render_prometheus(), media_type='text/plain; version=0.0.4')
