from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.api.error_handlers import register_exception_handlers
from app.api.routes import router
from app.core.dependencies import container
from app.core.observability import configure_telemetry
from app.core.settings import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await container.relational_repo.init_schema()
    yield
    await container.telemetry_publisher.close()


favicon_path = Path(__file__).resolve().parent / 'static' / 'favicon.svg'

app = FastAPI(
    title=settings.app_name,
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
    return FileResponse(favicon_path, media_type='image/svg+xml')


@app.get('/favicon.ico', include_in_schema=False)
async def favicon_ico() -> FileResponse:
    return FileResponse(favicon_path, media_type='image/svg+xml')


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.app_env}
