"""Issue part route handler (POST /api/issues and GET /api/issues/mine)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_employee_or_admin
from app.models.user import User
from app.schemas.activity import MyIssuesResponse
from app.schemas.issue import IssueRequest, IssueResponse
from app.services.activity_service import get_my_issues
from app.services.issue_service import issue_part

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get(
    "/mine",
    response_model=MyIssuesResponse,
    summary="Get authenticated employee's own issue history",
)
def get_mine(
    q: Optional[str] = Query(None, description="Search by part name or part number"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD) inclusive"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD) inclusive"),
    sort: str = Query("created_at", description="Sort field: created_at, part_name, quantity"),
    order: str = Query("desc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee_or_admin),
) -> MyIssuesResponse:
    """Retrieve issue transactions performed by the authenticated caller."""
    return get_my_issues(
        db=db,
        current_user=current_user,
        q=q,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a spare part from an inventory location",
)
def create_issue(
    data: IssueRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee_or_admin),
) -> IssueResponse:
    """Issue a spare part atomically.

    Deducts stock immediately without approval, writes an ISSUED transaction,
    creates in-app notifications for admins, and supports idempotent replays.
    """
    res, status_code = issue_part(db=db, user=current_user, data=data)
    response.status_code = status_code
    return res

