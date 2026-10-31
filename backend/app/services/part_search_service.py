"""Search service for employee part discovery (Module 6A)."""

from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select, case, literal_column, text
from sqlalchemy.orm import Session

from app.models.spare_part import SparePart
from app.models.machine import Machine
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.user import User
from app.schemas.part_public import PartCard, PrimaryLocation
from app.schemas.common import Page
from app.services.stock_rules import is_low_stock
from app.core.storage import storage_service


def _escape_like(term: str) -> str:
    """Escape % _ \\ for ILIKE."""
    return term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _build_relevance_score(terms: List[str]):
    """Return a CASE expression that scores each term."""
    score_expr = literal_column('0')
    for term in terms:
        esc = f"%{_escape_like(term)}%"
        # exact part_number
        score_expr = score_expr + case((SparePart.part_number.ilike(term), 100), else_=0)
        # prefix part_number
        score_expr = score_expr + case((SparePart.part_number.ilike(f'{term}%'), 50), else_=0)
        # name starts with term
        score_expr = score_expr + case((SparePart.name.ilike(f'{term}%'), 40), else_=0)
        # name contains term
        score_expr = score_expr + case((SparePart.name.ilike(esc), 20), else_=0)
        # machine name/code match (active only via EXISTS subquery so machines isn't cartesian joined)
        mach_exists = SparePart.machines.any(
            Machine.is_active.is_(True) & (Machine.name.ilike(esc) | Machine.code.ilike(esc))
        )
        score_expr = score_expr + case(
            (mach_exists, 10),
            else_=0,
        )
    return score_expr


def search_parts(
    db: Session,
    user: User,
    q: Optional[str] = None,
    category: Optional[str] = None,
    machine_id: Optional[int] = None,
    location_id: Optional[int] = None,
    availability: str = 'all',
    sort: str = 'relevance',
    order: str = 'desc',
    page: int = 1,
    page_size: int = 12,
) -> Page[PartCard]:
    """Core search implementation – returns a paginated Page[PartCard]."""

    if page < 1:
        raise HTTPException(status_code=422, detail='page must be >= 1')
    if not (1 <= page_size <= 48):
        raise HTTPException(status_code=422, detail='page_size must be 1‑48')

    stmt = (
        select(
            SparePart.id,
            SparePart.part_number,
            SparePart.name,
            SparePart.category,
            SparePart.manufacturer,
            SparePart.description,
            SparePart.image_path,
            SparePart.is_active,
            func.coalesce(func.sum(Inventory.quantity), 0).label('total_quantity'),
            func.count(
                func.distinct(
                    case((Inventory.quantity > 0, Inventory.location_id), else_=None)
                )
            ).label('location_count_with_stock'),
        )
        .select_from(SparePart)
        .join(Inventory, SparePart.inventory_items, isouter=True)
        .join(Location, Inventory.location_id == Location.id, isouter=True)
        .where(SparePart.is_active.is_(True))
        .where(Location.is_active.is_(True) | (Location.id.is_(None)))
        .group_by(SparePart.id)
    )

    if q:
        terms = [t for t in q.split() if t][:5]
        relevance = _build_relevance_score(terms)
        stmt = stmt.add_columns(relevance.label('relevance_score'))
        for term in terms:
            esc = f"%{_escape_like(term)}%"
            stmt = stmt.where(
                SparePart.part_number.ilike(esc)
                | SparePart.name.ilike(esc)
                | SparePart.category.ilike(esc)
                | SparePart.manufacturer.ilike(esc)
                | SparePart.description.ilike(esc)
                | SparePart.machines.any(
                    Machine.is_active.is_(True) & (Machine.name.ilike(esc) | Machine.code.ilike(esc))
                )
            )
    else:
        stmt = stmt.add_columns(literal_column('0').label('relevance_score'))

    if category:
        stmt = stmt.where(SparePart.category == category)
    if machine_id:
        stmt = stmt.where(
            SparePart.machines.any(
                (Machine.id == machine_id) & Machine.is_active.is_(True)
            )
        )

    if availability not in {'all', 'available', 'my_location', 'location'}:
        raise HTTPException(status_code=422, detail='Invalid availability value')
    if availability == 'available':
        stmt = stmt.having(func.coalesce(func.sum(Inventory.quantity), 0) > 0)
    elif availability == 'location':
        if not location_id:
            raise HTTPException(status_code=422, detail='location_id required when availability=location')
        stmt = stmt.where(Inventory.location_id == location_id, Inventory.quantity > 0)

    sort_whitelist = {'relevance', 'name', 'part_number', 'availability'}
    if sort not in sort_whitelist:
        raise HTTPException(status_code=422, detail='Invalid sort field')
    order_fn = {'asc': lambda c: c.asc(), 'desc': lambda c: c.desc()}.get(order)
    if not order_fn:
        raise HTTPException(status_code=422, detail='Invalid order value')

    if sort == 'relevance':
        stmt = stmt.order_by(order_fn(literal_column('relevance_score')), SparePart.id)
    elif sort == 'name':
        stmt = stmt.order_by(order_fn(SparePart.name), SparePart.id)
    elif sort == 'part_number':
        stmt = stmt.order_by(order_fn(SparePart.part_number), SparePart.id)
    else:  # availability ordering
        stock_order = case(
            (func.coalesce(func.sum(Inventory.quantity), 0) == 0, 0),
            (is_low_stock(func.coalesce(func.sum(Inventory.quantity), 0), 0), 1),
            else_=2,
        )
        stmt = stmt.order_by(order_fn(stock_order), SparePart.name)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    parts_rows = db.execute(stmt).fetchall()
    part_ids = [r.id for r in parts_rows]

    # --- machines batch ---
    from app.models.part_machine import PartMachine
    machines_q = (
        select(
            PartMachine.part_id,
            Machine.id,
            Machine.name,
            Machine.code,
        )
        .join(Machine, Machine.id == PartMachine.machine_id)
        .where(PartMachine.part_id.in_(part_ids), Machine.is_active.is_(True))
    )
    machines_rows = db.execute(machines_q).fetchall()
    machines_map = {}
    for r in machines_rows:
        machines_map.setdefault(r.part_id, []).append({'id': r.id, 'name': r.name, 'code': r.code})

    # --- primary location batch ---
    primary_q = (
        select(
            Inventory.part_id,
            Inventory.location_id,
            Inventory.quantity,
            Inventory.store_name,
            Inventory.rack,
            Inventory.bin,
            Location.id.label("loc_id"),
            Location.name.label("loc_name"),
            Location.code.label("loc_code"),
            literal_column('true').label('is_my_location'),
        )
        .join(Location, Inventory.location_id == Location.id)
        .where(
            Inventory.part_id.in_(part_ids),
            Inventory.location_id == user.location_id,
            Location.is_active.is_(True),
        )
    )
    primary_rows = db.execute(primary_q).fetchall()
    primary_map = {r.part_id: r for r in primary_rows}

    missing = [pid for pid in part_ids if pid not in primary_map]
    if missing:
        alt_q = (
            select(
                Inventory.part_id,
                Inventory.location_id,
                Inventory.quantity,
                Inventory.store_name,
                Inventory.rack,
                Inventory.bin,
                Location.id.label("loc_id"),
                Location.name.label("loc_name"),
                Location.code.label("loc_code"),
                literal_column('false').label('is_my_location'),
            )
            .join(Location, Inventory.location_id == Location.id)
            .where(Inventory.part_id.in_(missing), Location.is_active.is_(True))
            .order_by(Inventory.part_id, Inventory.quantity.desc(), Location.name)
        )
        alt_rows = db.execute(alt_q).fetchall()
        seen = set()
        for r in alt_rows:
            if r.part_id not in seen:
                primary_map[r.part_id] = r
                seen.add(r.part_id)

    items: List[PartCard] = []
    for row in parts_rows:
        pid = row.id
        machs = machines_map.get(pid, [])[:5]
        machine_briefs = [{'id': m['id'], 'name': m['name'], 'code': m['code']} for m in machs]
        prim = primary_map.get(pid)
        if prim:
            primary_location = PrimaryLocation(
                location={'id': prim.loc_id, 'name': prim.loc_name, 'code': prim.loc_code},
                quantity=prim.quantity,
                store_name=prim.store_name,
                rack=prim.rack,
                bin=prim.bin,
                is_my_location=prim.is_my_location,
            )
        else:
            primary_location = None
        # other locations with stock (excluding primary)
        other_q = (
            select(Location.id, Location.name, Location.code)
            .join(Inventory, Inventory.location_id == Location.id)
            .where(Inventory.part_id == pid, Inventory.quantity > 0, Location.is_active.is_(True))
        )
        other_rows = db.execute(other_q).fetchall()
        other_locs = [
            {'id': r.id, 'name': r.name, 'code': r.code}
            for r in other_rows
            if not primary_location or r.id != primary_location.location.id
        ]
        other_loc_count = len(other_locs)
        if row.total_quantity == 0:
            avail = 'OUT_OF_STOCK'
        elif is_low_stock(row.total_quantity, 0):
            avail = 'LOW_STOCK'
        else:
            avail = 'IN_STOCK'
        img_url = storage_service.public_url(row.image_path) if row.image_path else None
        items.append(
            PartCard(
                id=pid,
                part_number=row.part_number,
                name=row.name,
                category=row.category,
                manufacturer=row.manufacturer,
                short_description=row.description,
                image_url=img_url,
                machines=machine_briefs,
                machine_count_total=len(machs),
                total_quantity=row.total_quantity,
                location_count_with_stock=row.location_count_with_stock,
                availability_status=avail,
                primary_location=primary_location,
                other_locations_with_stock=other_loc_count,
            )
        )

    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
    return Page[PartCard](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
