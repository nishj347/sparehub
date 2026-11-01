import os
import time
import uuid
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import logger, setup_logging

settings = get_settings()
setup_logging(settings.APP_ENV)

MAX_BODY_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB

app = FastAPI(
    title="Spare Parts Management & Discovery System API",
    description="Enterprise REST API for spare parts catalog, inventory management, and issue tracking.",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Optional TrustedHostMiddleware
if settings.ALLOWED_HOSTS:
    allowed_hosts = [h.strip() for h in settings.ALLOWED_HOSTS.split(",") if h.strip()]
    if allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Configure CORS restricted strictly to origins defined in settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    """Enforce body size limits, inject request ID, log requests, and attach security headers."""
    # 1. Body size limit (8 MB)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_BODY_SIZE_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body too large", "code": "request_too_large"},
                )
        except ValueError:
            pass

    # 2. Request ID & Timing
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} {response.status_code} {duration_ms:.2f}ms"
    )

    response.headers["X-Request-ID"] = request_id

    # 3. Security headers
    path = request.url.path
    if path.startswith("/api/"):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    elif path.startswith("/uploads/"):
        response.headers["X-Content-Type-Options"] = "nosniff"

    return response


# Mount all API routes under /api
app.include_router(api_router, prefix="/api")

# Static files for image uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions with consistent JSON response schema."""
    code = getattr(exc, "code", f"HTTP_{exc.status_code}")
    content: dict = {
        "detail": exc.detail,
        "code": code,
    }
    if hasattr(exc, "field") and exc.field is not None:
        content["field"] = exc.field
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with consistent JSON response schema."""
    errors = exc.errors()
    content: dict = {
        "detail": jsonable_encoder(errors),
        "code": "validation_error",
    }
    if errors:
        loc = errors[0].get("loc", ())
        if len(loc) > 1 and loc[0] == "body":
            content["field"] = str(loc[1])
        elif loc:
            content["field"] = str(loc[-1])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=content,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled server exceptions. Internal details masked in production."""
    logger.exception(f"Unhandled server exception on {request.method} {request.url.path}: {exc}")
    detail = "Internal server error" if settings.is_production else str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
            "code": "INTERNAL_SERVER_ERROR",
        },
    )
