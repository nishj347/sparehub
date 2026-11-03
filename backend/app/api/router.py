from fastapi import APIRouter

from app.api.routes import (
    admin_activity,
    admin_dashboard,
    admin_inventory,
    admin_locations,
    admin_machines,
    admin_notifications,
    admin_parts,
    admin_surplus,
    admin_users,
    auth,
    health,
    issues,
    parts,
    surplus,
)

api_router = APIRouter()

# Mount health routes under /health
api_router.include_router(health.router)

# Mount authentication routes under /auth
api_router.include_router(auth.router)

# Mount master data administration routes under /admin
api_router.include_router(admin_dashboard.router)
api_router.include_router(admin_locations.router)
api_router.include_router(admin_machines.router)
api_router.include_router(admin_parts.router)
api_router.include_router(admin_inventory.router)
api_router.include_router(admin_activity.router)
api_router.include_router(admin_notifications.router)
api_router.include_router(admin_surplus.router)
api_router.include_router(admin_users.router)
api_router.include_router(parts.router)
api_router.include_router(issues.router)
api_router.include_router(surplus.router)
