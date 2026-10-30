from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()

# Mount health routes under /health
api_router.include_router(health.router)
