from fastapi import APIRouter

from app.api.routes import (
    admin_inventory,
    admin_locations,
    admin_machines,
    admin_parts,
    auth,
    health,
)

api_router = APIRouter()

# Mount health routes under /health
api_router.include_router(health.router)

# Mount authentication routes under /auth
api_router.include_router(auth.router)

# Mount master data administration routes under /admin
api_router.include_router(admin_locations.router)
api_router.include_router(admin_machines.router)
api_router.include_router(admin_parts.router)
api_router.include_router(admin_inventory.router)
