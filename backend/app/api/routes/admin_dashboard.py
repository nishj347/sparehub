"""Admin Dashboard endpoint (GET /api/admin/dashboard)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import get_admin_dashboard

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin Dashboard"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get operational overview metrics, low stock alerts, and recent transactions for Admin Dashboard",
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DashboardResponse:
    """Retrieve key operational statistics, low stock parts, and recent ledger activity for administrators."""
    return get_admin_dashboard(db=db)

