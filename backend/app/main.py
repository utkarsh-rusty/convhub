import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.realtime.manager import get_ws_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    app.state.engine = engine
    app.state.session_factory = session_factory

    ws_manager = get_ws_manager()
    await ws_manager.start()
    app.state.ws_manager = ws_manager

    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    yield
    await ws_manager.stop()
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    enable_openapi = settings.debug or settings.app_env == "development"

    app = FastAPI(
        title="ConvHub API",
        version="0.1.0",
        description="Shared AI Workspace API",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if enable_openapi else None,
        redoc_url="/redoc" if enable_openapi else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
