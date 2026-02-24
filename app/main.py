from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.api.routes import router
from app.core.dependencies import container
from app.core.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await container.relational_repo.init_schema()
    yield
    await container.telemetry_publisher.close()


favicon_path = Path(__file__).resolve().parent / 'static' / 'favicon.svg'

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(router)


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
    return FileResponse(favicon_path, media_type='image/svg+xml')


@app.get('/favicon.ico', include_in_schema=False)
async def favicon_ico() -> FileResponse:
    return FileResponse(favicon_path, media_type='image/svg+xml')


@app.get(
    '/health',
    tags=['telemetria'],
    summary='Healthcheck da API',
    description='Endpoint de verificação rápida de disponibilidade da API e ambiente ativo.',
)
async def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.app_env}
