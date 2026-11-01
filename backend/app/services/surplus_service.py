import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import (
    and_,
    case,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session, joinedload
from starlette import status

from app.core.exceptions import AppHTTPException
from app.core.storage import storage_service
from app.models.enums import UserRole
from app.models.location import Location
from app.models.notification import Notification
from app.models.spare_part import SparePart
from app.models.surplus import (
    SurplusCondition,
    SurplusInterest,
    SurplusItem,
    SurplusKind,
    SurplusStatus,
)
from app.models.user import User
from app.schemas.common import Page
from app.schemas.surplus import (
    AdminInterestUserSummary,
    AdminSurplusInterestRecord,
    MyInterestSummary,
    MySurplusInterestItem,
    SurplusFiltersResponse,
    SurplusInterestCreate,
    SurplusInterestResponse,
    SurplusItemCreate,
    SurplusItemDetail,
    SurplusItemList,
    SurplusItemUpdate,
    SurplusLocationSummary,
    SurplusPartSummary,
    SurplusUserSummary,
)


def escape_like(val: str) -> str:
    """Escape SQL ILIKE wildcards to prevent pattern injection."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_item_list_dto(
    item: SurplusItem,
    user: User,
    my_interest: Optional[SurplusInterest] = None,
) -> SurplusItemList:
    return SurplusItemList(
        id=item.id,
        title=item.title,
        kind=SurplusKind(item.kind),
        condition=SurplusCondition(item.condition),
        quantity=item.quantity,
        unit=item.unit,
        status=SurplusStatus(item.status),
        image_url=storage_service.public_url(item.image_path),
        location=SurplusLocationSummary.model_validate(item.location),
        storage_details=item.storage_details,
        valid_until=item.valid_until,
        part=SurplusPartSummary.model_validate(item.part) if item.part else None,
        is_my_location=item.location_id == user.location_id,
        listed_at=item.created_at,
        my_interest=(
            MyInterestSummary(
                quantity_requested=my_interest.quantity_requested,
                message=my_interest.message,
            )
            if my_interest
            else None
        ),
    )


def _build_item_detail_dto(
    item: SurplusItem,
    user: User,
    my_interest: Optional[SurplusInterest] = None,
) -> SurplusItemDetail:
    return SurplusItemDetail(
        id=item.id,
        title=item.title,
        kind=SurplusKind(item.kind),
        condition=SurplusCondition(item.condition),
        quantity=item.quantity,
        unit=item.unit,
        status=SurplusStatus(item.status),
        image_url=storage_service.public_url(item.image_path),
        location=SurplusLocationSummary.model_validate(item.location),
        storage_details=item.storage_details,
        valid_until=item.valid_until,
        part=SurplusPartSummary.model_validate(item.part) if item.part else None,
        is_my_location=item.location_id == user.location_id,
        listed_at=item.created_at,
        description=item.description,
        contact_note=item.contact_note,
        listed_by=SurplusUserSummary(
            name=item.creator.name,
            employee_id=item.creator.employee_id,
        ),
        my_interest=(
            MyInterestSummary(
                quantity_requested=my_interest.quantity_requested,
                message=my_interest.message,
            )
            if my_interest
            else None
        ),
    )


def list_surplus_items(
    db: Session,
    user: User,
    q: Optional[str] = None,
    kind: Optional[str] = None,
    location_id: Optional[int] = None,
    condition: Optional[str] = None,
    status_filter: Optional[str] = None,
    created_by: Optional[int] = None,
    sort: str = "newest",
    order: str = "desc",
    page: int = 1,
    page_size: int = 12,
    is_admin_view: bool = False,
) -> Page[SurplusItemList]:
    """Search and browse surplus items with strict visibility and own-location-first sorting."""
    page_size = max(1, min(page_size, 48))
    page = max(1, page)

    # Base query joined with location and optional spare_part
    base_query = (
        select(SurplusItem)
        .join(Location, SurplusItem.location_id == Location.id)
        .outerjoin(SparePart, SurplusItem.part_id == SparePart.id)
    )

    filters = []

    # Non-admin visibility constraints
    if not is_admin_view:
        filters.append(
            SurplusItem.status.in_(
                [SurplusStatus.AVAILABLE.value, SurplusStatus.RESERVED.value]
            )
        )
        filters.append(
            or_(
                SurplusItem.valid_until.is_(None),
                SurplusItem.valid_until >= func.current_date(),
            )
        )
        filters.append(Location.is_active.is_(True))
    else:
        if status_filter:
            filters.append(SurplusItem.status == status_filter)
        if created_by:
            filters.append(SurplusItem.created_by == created_by)

    # Common filters
    if kind:
        filters.append(SurplusItem.kind == kind)
    if location_id:
        filters.append(SurplusItem.location_id == location_id)
    if condition:
        filters.append(SurplusItem.condition == condition)

    # Free-text multi-term search
    if q and q.strip():
        terms = [t.strip() for t in q.strip().split() if t.strip()]
        for term in terms:
            escaped = f"%{escape_like(term)}%"
            term_clause = or_(
                SurplusItem.title.ilike(escaped),
                SurplusItem.description.ilike(escaped),
                SparePart.part_number.ilike(escaped),
                SparePart.name.ilike(escaped),
            )
            filters.append(term_clause)

    if filters:
        base_query = base_query.where(and_(*filters))

    # Count query
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_items = db.scalar(count_stmt) or 0
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    # Sorting
    sort_clean = sort.lower().strip() if sort else "newest"
    order_clean = order.lower().strip() if order else "desc"
    is_desc = order_clean == "desc"

    order_clauses = []
    if sort_clean == "newest":
        # Own location sorts first for regular users
        if not is_admin_view and user.location_id:
            order_clauses.append(
                case((SurplusItem.location_id == user.location_id, 0), else_=1)
            )
        order_clauses.append(
            SurplusItem.created_at.desc() if is_desc else SurplusItem.created_at.asc()
        )
        order_clauses.append(SurplusItem.id.desc())
    elif sort_clean == "title":
        order_clauses.append(
            func.lower(SurplusItem.title).desc()
            if is_desc
            else func.lower(SurplusItem.title).asc()
        )
        order_clauses.append(SurplusItem.id.desc())
    elif sort_clean == "quantity":
        order_clauses.append(
            SurplusItem.quantity.desc() if is_desc else SurplusItem.quantity.asc()
        )
        order_clauses.append(SurplusItem.id.desc())
    else:
        order_clauses.append(SurplusItem.created_at.desc())
        order_clauses.append(SurplusItem.id.desc())

    # Fetch page items
    fetch_stmt = (
        base_query.options(
            joinedload(SurplusItem.location),
            joinedload(SurplusItem.part),
        )
        .order_by(*order_clauses)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.scalars(fetch_stmt).unique().all()

    # Preload caller's interest for returned items in a single query
    interests_map = {}
    if items:
        item_ids = [it.id for it in items]
        interests = db.scalars(
            select(SurplusInterest).where(
                SurplusInterest.item_id.in_(item_ids),
                SurplusInterest.user_id == user.id,
            )
        ).all()
        for intr in interests:
            interests_map[intr.item_id] = intr

    items_dto = [_build_item_list_dto(it, user, interests_map.get(it.id)) for it in items]

    return Page[SurplusItemList](
        items=items_dto,
        total=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_surplus_filters(db: Session) -> SurplusFiltersResponse:
    """Return available kinds, conditions, and active locations that have listings."""
    # Active locations with available/reserved listings
    loc_stmt = (
        select(Location)
        .join(SurplusItem, SurplusItem.location_id == Location.id)
        .where(
            Location.is_active.is_(True),
            SurplusItem.status.in_(
                [SurplusStatus.AVAILABLE.value, SurplusStatus.RESERVED.value]
            ),
            or_(
                SurplusItem.valid_until.is_(None),
                SurplusItem.valid_until >= func.current_date(),
            ),
        )
        .distinct()
        .order_by(Location.name)
    )
    locations = db.scalars(loc_stmt).all()

    return SurplusFiltersResponse(
        kinds=[k.value for k in SurplusKind],
        conditions=[c.value for c in SurplusCondition],
        locations=[SurplusLocationSummary.model_validate(loc) for loc in locations],
    )


def get_surplus_item_detail(
    db: Session,
    item_id: int,
    user: User,
    is_admin_view: bool = False,
) -> SurplusItemDetail:
    """Retrieve full surplus item detail with role-appropriate visibility guards."""
    stmt = (
        select(SurplusItem)
        .options(
            joinedload(SurplusItem.location),
            joinedload(SurplusItem.part),
            joinedload(SurplusItem.creator),
        )
        .where(SurplusItem.id == item_id)
    )
    item = db.scalar(stmt)
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    # Employee visibility checks
    if not is_admin_view:
        if item.status in [SurplusStatus.CLAIMED.value, SurplusStatus.WITHDRAWN.value]:
            raise AppHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus item not found.",
                code="not_found",
            )
        if not item.location.is_active:
            raise AppHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus item not found.",
                code="not_found",
            )
        if item.valid_until and item.valid_until < date.today():
            raise AppHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surplus item listing has expired.",
                code="expired_listing",
            )

    # Fetch user's interest if any
    my_interest = db.scalar(
        select(SurplusInterest).where(
            SurplusInterest.item_id == item_id,
            SurplusInterest.user_id == user.id,
        )
    )

    return _build_item_detail_dto(item, user, my_interest)


def upsert_interest(
    db: Session,
    item_id: int,
    user: User,
    data: SurplusInterestCreate,
) -> SurplusInterestResponse:
    """Create or update caller's interest on an available item and trigger admin notifications."""
    item = db.scalar(
        select(SurplusItem)
        .where(SurplusItem.id == item_id)
        .with_for_update()
    )
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    if item.status not in [SurplusStatus.AVAILABLE.value, SurplusStatus.RESERVED.value]:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interest can only be expressed on AVAILABLE or RESERVED items.",
            code="invalid_item_status",
        )

    if item.created_by == user.id:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot express interest in your own listing.",
            code="own_listing",
        )

    if data.quantity_requested > item.quantity:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Requested quantity ({data.quantity_requested}) exceeds available quantity ({item.quantity}).",
            code="quantity_exceeds_available",
            field="quantity_requested",
        )

    # Upsert interest
    existing_interest = db.scalar(
        select(SurplusInterest)
        .where(
            SurplusInterest.item_id == item.id,
            SurplusInterest.user_id == user.id,
        )
        .with_for_update()
    )

    if existing_interest:
        existing_interest.quantity_requested = data.quantity_requested
        existing_interest.message = data.message
        interest_record = existing_interest
    else:
        new_interest = SurplusInterest(
            item_id=item.id,
            user_id=user.id,
            quantity_requested=data.quantity_requested,
            message=data.message,
        )
        db.add(new_interest)
        interest_record = new_interest

    db.flush()

    # Notification Handling:
    # Check if a notification for this user and item was created within the last 5 minutes
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    recent_notif = db.scalar(
        select(Notification).where(
            Notification.surplus_item_id == item.id,
            Notification.created_at >= five_min_ago,
            Notification.message.like(f"{user.name}%"),
        )
    )

    if not recent_notif:
        # Determine recipient admin list:
        # Active STORE_ADMIN at item's location + creator
        admins_at_location = db.scalars(
            select(User).where(
                User.role == UserRole.STORE_ADMIN,
                User.location_id == item.location_id,
                User.is_active.is_(True),
            )
        ).all()

        recipient_ids = {a.id for a in admins_at_location}

        # Check item creator
        creator = db.scalar(select(User).where(User.id == item.created_by))
        if creator and creator.is_active:
            recipient_ids.add(creator.id)

        # Fallback to all active admins if empty
        if not recipient_ids:
            all_admins = db.scalars(
                select(User).where(
                    User.role == UserRole.STORE_ADMIN,
                    User.is_active.is_(True),
                )
            ).all()
            recipient_ids = {a.id for a in all_admins}

        user_loc_name = user.location.name if user.location else "Unknown"
        notification_text = (
            f"{user.name} ({user.employee_id}, {user_loc_name}) is interested in "
            f"{data.quantity_requested} {item.unit} of {item.title} at {item.location.name}."
        )

        for recipient_id in recipient_ids:
            db.add(
                Notification(
                    recipient_user_id=recipient_id,
                    surplus_item_id=item.id,
                    message=notification_text,
                )
            )

    db.commit()
    db.refresh(interest_record)

    return SurplusInterestResponse(
        id=interest_record.id,
        item_id=interest_record.item_id,
        quantity_requested=interest_record.quantity_requested,
        message=interest_record.message,
        created_at=interest_record.created_at,
    )


def withdraw_interest(db: Session, item_id: int, user: User) -> None:
    """Withdraw caller's interest on a surplus item (idempotent)."""
    interest = db.scalar(
        select(SurplusInterest).where(
            SurplusInterest.item_id == item_id,
            SurplusInterest.user_id == user.id,
        )
    )
    if interest:
        db.delete(interest)
        db.commit()


def list_my_interests(
    db: Session,
    user: User,
    page: int = 1,
    page_size: int = 20,
) -> Page[MySurplusInterestItem]:
    """Retrieve all surplus interests registered by the logged-in user."""
    page_size = max(1, min(page_size, 48))
    page = max(1, page)

    base_query = (
        select(SurplusInterest)
        .join(SurplusItem, SurplusInterest.item_id == SurplusItem.id)
        .where(SurplusInterest.user_id == user.id)
    )

    count_stmt = select(func.count(SurplusInterest.id)).where(
        SurplusInterest.user_id == user.id
    )
    total_items = db.scalar(count_stmt) or 0
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    interests = db.scalars(
        base_query.options(
            joinedload(SurplusInterest.item).joinedload(SurplusItem.location),
            joinedload(SurplusInterest.item).joinedload(SurplusItem.part),
        )
        .order_by(SurplusInterest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items_dto = [
        MySurplusInterestItem(
            id=intr.id,
            quantity_requested=intr.quantity_requested,
            message=intr.message,
            created_at=intr.created_at,
            item=_build_item_list_dto(intr.item, user, intr),
        )
        for intr in interests
    ]

    return Page[MySurplusInterestItem](
        items=items_dto,
        total=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_surplus_item(
    db: Session,
    admin: User,
    data: SurplusItemCreate,
) -> SurplusItemDetail:
    """Create a new surplus listing as an administrator."""
    # 1. Validate location
    location = db.scalar(select(Location).where(Location.id == data.location_id))
    if not location or not location.is_active:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or inactive location.",
            code="invalid_location",
            field="location_id",
        )

    # 2. Validate part_id if given
    if data.part_id:
        part = db.scalar(select(SparePart).where(SparePart.id == data.part_id))
        if not part:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Spare part with ID {data.part_id} does not exist.",
                code="invalid_part",
                field="part_id",
            )

    # 3. Validate valid_until not in past
    if data.valid_until and data.valid_until < date.today():
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="valid_until cannot be in the past.",
            code="invalid_valid_until",
            field="valid_until",
        )

    new_item = SurplusItem(
        title=data.title,
        kind=data.kind.value,
        quantity=data.quantity,
        unit=data.unit,
        condition=data.condition.value,
        location_id=data.location_id,
        description=data.description,
        storage_details=data.storage_details,
        contact_note=data.contact_note,
        part_id=data.part_id,
        status=SurplusStatus.AVAILABLE.value,
        valid_until=data.valid_until,
        created_by=admin.id,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return get_surplus_item_detail(db, new_item.id, admin, is_admin_view=True)


def update_surplus_item(
    db: Session,
    item_id: int,
    admin: User,
    data: SurplusItemUpdate,
) -> SurplusItemDetail:
    """Update fields on an existing surplus item."""
    item = db.scalar(select(SurplusItem).where(SurplusItem.id == item_id).with_for_update())
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    update_dict = data.model_dump(exclude_unset=True)
    if not update_dict:
        raise AppHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided for update.",
            code="empty_update",
        )

    if "location_id" in update_dict and update_dict["location_id"] is not None:
        loc = db.scalar(select(Location).where(Location.id == update_dict["location_id"]))
        if not loc or not loc.is_active:
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid or inactive location.",
                code="invalid_location",
                field="location_id",
            )
        item.location_id = update_dict["location_id"]

    if "part_id" in update_dict:
        part_id = update_dict["part_id"]
        if part_id is not None:
            part = db.scalar(select(SparePart).where(SparePart.id == part_id))
            if not part:
                raise AppHTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Spare part with ID {part_id} does not exist.",
                    code="invalid_part",
                    field="part_id",
                )
        item.part_id = part_id

    if "valid_until" in update_dict:
        v_until = update_dict["valid_until"]
        if v_until and v_until < date.today():
            raise AppHTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="valid_until cannot be in the past.",
                code="invalid_valid_until",
                field="valid_until",
            )
        item.valid_until = v_until

    if "title" in update_dict and update_dict["title"] is not None:
        item.title = update_dict["title"]
    if "kind" in update_dict and update_dict["kind"] is not None:
        item.kind = update_dict["kind"].value if hasattr(update_dict["kind"], "value") else str(update_dict["kind"])
    if "quantity" in update_dict and update_dict["quantity"] is not None:
        item.quantity = update_dict["quantity"]
    if "unit" in update_dict and update_dict["unit"] is not None:
        item.unit = update_dict["unit"]
    if "condition" in update_dict and update_dict["condition"] is not None:
        item.condition = update_dict["condition"].value if hasattr(update_dict["condition"], "value") else str(update_dict["condition"])
    if "description" in update_dict:
        item.description = update_dict["description"]
    if "storage_details" in update_dict:
        item.storage_details = update_dict["storage_details"]
    if "contact_note" in update_dict:
        item.contact_note = update_dict["contact_note"]

    db.commit()
    db.refresh(item)

    return get_surplus_item_detail(db, item.id, admin, is_admin_view=True)


def update_surplus_status(
    db: Session,
    item_id: int,
    admin: User,
    new_status: SurplusStatus,
) -> SurplusItemDetail:
    """Transition surplus item lifecycle status."""
    item = db.scalar(select(SurplusItem).where(SurplusItem.id == item_id).with_for_update())
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    current_status = SurplusStatus(item.status)
    target_status = new_status

    if current_status == target_status:
        return get_surplus_item_detail(db, item.id, admin, is_admin_view=True)

    if current_status == SurplusStatus.CLAIMED:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CLAIMED status is final and cannot be transitioned.",
            code="invalid_transition",
        )

    allowed = False
    if current_status == SurplusStatus.AVAILABLE:
        allowed = target_status in [
            SurplusStatus.RESERVED,
            SurplusStatus.CLAIMED,
            SurplusStatus.WITHDRAWN,
        ]
    elif current_status == SurplusStatus.RESERVED:
        allowed = target_status in [
            SurplusStatus.AVAILABLE,
            SurplusStatus.CLAIMED,
            SurplusStatus.WITHDRAWN,
        ]
    elif current_status == SurplusStatus.WITHDRAWN:
        allowed = target_status == SurplusStatus.AVAILABLE

    if not allowed:
        raise AppHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition from {current_status.value} to {target_status.value}.",
            code="invalid_transition",
        )

    item.status = target_status.value
    db.commit()
    db.refresh(item)

    return get_surplus_item_detail(db, item.id, admin, is_admin_view=True)


def upload_surplus_image(
    db: Session,
    item_id: int,
    file_bytes: bytes,
) -> str:
    """Validate image bytes, store file, update surplus record, and clean up previous image."""
    item = db.scalar(select(SurplusItem).where(SurplusItem.id == item_id).with_for_update())
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    old_image_path = item.image_path
    new_relative_path = storage_service.save_image(file_bytes)

    item.image_path = new_relative_path
    db.commit()

    if old_image_path:
        storage_service.delete(old_image_path)

    return storage_service.public_url(new_relative_path) or ""


def delete_surplus_image(db: Session, item_id: int) -> None:
    """Delete surplus item image and clear record reference."""
    item = db.scalar(select(SurplusItem).where(SurplusItem.id == item_id).with_for_update())
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    old_image_path = item.image_path
    item.image_path = None
    db.commit()

    if old_image_path:
        storage_service.delete(old_image_path)


def get_item_interests(
    db: Session,
    item_id: int,
    admin: User,
) -> List[AdminSurplusInterestRecord]:
    """Retrieve full interest roster for an item (Admin only)."""
    item = db.scalar(select(SurplusItem).where(SurplusItem.id == item_id))
    if not item:
        raise AppHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surplus item not found.",
            code="not_found",
        )

    stmt = (
        select(SurplusInterest)
        .options(
            joinedload(SurplusInterest.user).joinedload(User.location),
        )
        .where(SurplusInterest.item_id == item_id)
        .order_by(SurplusInterest.created_at.desc())
    )
    interests = db.scalars(stmt).all()

    return [
        AdminSurplusInterestRecord(
            id=intr.id,
            user=AdminInterestUserSummary(
                name=intr.user.name,
                employee_id=intr.user.employee_id,
                location=SurplusLocationSummary.model_validate(intr.user.location),
            ),
            quantity_requested=intr.quantity_requested,
            message=intr.message,
            created_at=intr.created_at,
        )
        for intr in interests
    ]

