from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import logger, setup_logging

settings = get_settings()
setup_logging(settings.APP_ENV)

app = FastAPI(
    title="Spare Parts Management & Discovery System API",
    description="Enterprise REST API for spare parts catalog, inventory management, and issue tracking.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS restricted strictly to origins defined in settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount all API routes under /api
app.include_router(api_router, prefix="/api")


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
