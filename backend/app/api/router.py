from fastapi import APIRouter

from app.api.routes import admin_locations, admin_machines, auth, health

api_router = APIRouter()

# Mount health routes under /health
api_router.include_router(health.router)

# Mount authentication routes under /auth
api_router.include_router(auth.router)

# Mount master data administration routes under /admin
api_router.include_router(admin_locations.router)
api_router.include_router(admin_machines.router)
