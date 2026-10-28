"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.services.analysis import AnalysisService
from app.services.elexon_client import WindDataSource, create_data_source

logger = logging.getLogger(__name__)
UTC = timezone.utc


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level.upper(),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    root.setLevel(level.upper())


def create_app(settings: Settings | None = None, source: WindDataSource | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        data_source = source or create_data_source(app_settings)
        analysis_service = AnalysisService(app_settings, data_source)
        app.state.settings = app_settings
        app.state.data_source = data_source
        app.state.analysis_service = analysis_service
        logger.info(
            "Starting %s v%s in %s mode (data_mode=%s)",
            app_settings.app_name,
            app_settings.app_version,
            app_settings.environment,
            app_settings.data_mode,
        )

        prewarm_task: asyncio.Task[None] | None = None
        if app_settings.prewarm_default_range and not app_settings.is_fixture_mode:
            prewarm_task = asyncio.create_task(analysis_service.prewarm_default())

        try:
            yield
        finally:
            if prewarm_task is not None:
                prewarm_task.cancel()
                with suppress(asyncio.CancelledError):
                    await prewarm_task
            await data_source.close()
            logger.info("Application shutdown complete.")

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Day-ahead wind forecast selection and retrospective accuracy analytics for Great Britain. "
            "Forecasts are reconstructed strictly from versions published at or before each configured "
            "decision cut-off. Data sources: Elexon FUELHH (WIND outturn) and WINDFOR (wind forecast).\n\n"
            "Units are MW (average power over the delivery interval). WINDFOR is hourly; FUELHH is "
            "half-hourly and is averaged to the matching delivery hour. See /api/metadata for the full "
            "methodology and limitations."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Wind Forecast Analytics"},
        license_info={"name": "MIT"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = (request.headers.get("X-Request-ID") or "").strip()[:64] or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled error request_id=%s %s %s", request_id, request.method, request.url.path
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s %s %s -> %s (%.0f ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        if exc.status_code >= 500:
            logger.warning("Application error request_id=%s: %s (%s)", request_id, exc.message, exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(request_id),
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        errors = [
            {
                "field": ".".join(str(part) for part in error.get("loc", []) if part != "query"),
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        payload = {
            "error": {
                "code": "invalid_query",
                "message": "The request parameters are invalid.",
                "details": {"errors": errors},
                "request_id": request_id,
            }
        }
        return JSONResponse(
            status_code=422,
            content=payload,
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        messages = {
            404: "The requested resource was not found.",
            405: "The HTTP method is not allowed for this resource.",
        }
        payload = {
            "error": {
                "code": "not_found" if exc.status_code == 404 else "http_error",
                "message": messages.get(exc.status_code, str(exc.detail)),
                "details": {},
                "request_id": request_id,
            }
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled request failure request_id=%s", request_id, exc_info=exc)
        payload = {
            "error": {
                "code": "internal_error",
                "message": "An unexpected server error occurred. Please retry or contact the operator.",
                "details": {},
                "request_id": request_id,
            }
        }
        return JSONResponse(
            status_code=500,
            content=payload,
            headers={"X-Request-ID": request_id} if request_id else None,
        )

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "service": app_settings.app_name,
            "version": app_settings.app_version,
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()
