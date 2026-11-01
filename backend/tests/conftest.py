"""Pytest configuration, database isolation, fixtures, and factories."""
import os
import sys
from typing import Generator, Optional
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.rate_limit import login_rate_limiter
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.machine import Machine
from app.models.part_machine import PartMachine
from app.models.spare_part import SparePart
from app.models.user import User

settings = get_settings()

if "TEST_DATABASE_URL" in os.environ:
    TEST_DB_URL = os.environ["TEST_DATABASE_URL"]
else:
    TEST_DB_URL = settings.TEST_DATABASE_URL

if "DATABASE_URL" in os.environ:
    PROD_OR_DEV_DB_URL = os.environ["DATABASE_URL"]
else:
    PROD_OR_DEV_DB_URL = settings.DATABASE_URL


def validate_test_database_safety(test_url: Optional[str], primary_url: Optional[str]) -> str:
    """Enforce strict separation between production/dev database and test database."""
    if not test_url or not test_url.strip():
        sys.stderr.write(
            "\n[CRITICAL SAFETY ERROR] TEST_DATABASE_URL is not configured or empty.\n"
            "Tests must run against an isolated test database (e.g., .../sparehub_test).\n\n"
        )
        sys.stderr.flush()
        sys.exit(1)

    clean_test = test_url.strip()
    clean_primary = (primary_url or "").strip()

    if clean_test == clean_primary:
        sys.stderr.write(
            "\n[CRITICAL SAFETY ERROR] TEST_DATABASE_URL equals DATABASE_URL!\n"
            "Refusing to execute tests against development/production database.\n\n"
        )
        sys.stderr.flush()
        sys.exit(1)

    # Extract database name
    db_name = clean_test.split("/")[-1].split("?")[0]
    if not db_name.endswith("_test"):
        sys.stderr.write(
            f"\n[CRITICAL SAFETY ERROR] Test database '{db_name}' does not end with '_test'.\n"
            "Refusing to run tests against an unsafe database name.\n\n"
        )
        sys.stderr.flush()
        sys.exit(1)

    return clean_test


# Validate test DB immediately upon importing conftest
SAFE_TEST_URL = validate_test_database_safety(TEST_DB_URL, PROD_OR_DEV_DB_URL)
os.environ["DATABASE_URL"] = SAFE_TEST_URL
os.environ["ALEMBIC_DATABASE_URL"] = SAFE_TEST_URL

test_engine = create_engine(SAFE_TEST_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    """Apply Alembic migrations to the test database once per test session."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", SAFE_TEST_URL)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_database_and_rate_limits():
    """Truncate tables before each test and reset in-memory rate limiters."""
    login_rate_limiter.reset()
    with test_engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE notifications, inventory_transactions, inventory, "
                "part_machines, machines, spare_parts, users, locations RESTART IDENTITY CASCADE"
            )
        )
        conn.commit()
    yield
    login_rate_limiter.reset()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an isolated database session for a test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide FastAPI TestClient wired to the test database with per-request session isolation."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# FACTORY HELPERS
# ============================================================================

def create_location(
    db: Session,
    name: str = "Central Warehouse",
    code: str = "LOC01",
    city: str = "Pune",
    is_active: bool = True,
) -> Location:
    loc = Location(name=name, code=code, city=city, is_active=is_active)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def create_machine(
    db: Session,
    name: str = "CNC Milling Unit 1",
    code: str = "MCH01",
    is_active: bool = True,
    location: Optional[Location] = None,
) -> Machine:
    mach = Machine(
        name=name,
        code=code,
        is_active=is_active,
        location_id=location.id if location else None,
    )
    db.add(mach)
    db.commit()
    db.refresh(mach)
    return mach


def create_part(
    db: Session,
    part_number: str = "PRT-001",
    name: str = "Ball Bearing 6205",
    category: str = "Bearings",
    manufacturer: Optional[str] = "SKF",
    description: Optional[str] = None,
    specifications: Optional[dict] = None,
    is_active: bool = True,
    image_path: Optional[str] = None,
) -> SparePart:
    part = SparePart(
        part_number=part_number,
        name=name,
        category=category,
        manufacturer=manufacturer,
        description=description,
        specifications=specifications or {},
        is_active=is_active,
        image_path=image_path,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def create_user(
    db: Session,
    employee_id: str = "EMP001",
    name: str = "Test Employee",
    email: Optional[str] = None,
    role: UserRole = UserRole.EMPLOYEE,
    location: Optional[Location] = None,
    password: str = "TestPassword123!",
    is_active: bool = True,
) -> User:
    if email is None:
        email = f"{employee_id.lower()}@example.com"
    if location is None:
        location = db.scalar(select(Location).limit(1))
        if not location:
            location = create_location(db)

    user = User(
        employee_id=employee_id.upper(),
        name=name,
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        location_id=location.id,
        is_active=is_active,
        failed_login_attempts=0,
        locked_until=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_inventory(
    db: Session,
    part: SparePart,
    location: Location,
    quantity: int = 10,
    min_stock_level: int = 2,
    store_name: Optional[str] = "Main Store",
    rack: Optional[str] = "R-1",
    bin: Optional[str] = "B-01",
    record_initial_tx: bool = True,
    user: Optional[User] = None,
) -> Inventory:
    inv = Inventory(
        part_id=part.id,
        location_id=location.id,
        quantity=quantity,
        min_stock_level=min_stock_level,
        store_name=store_name,
        rack=rack,
        bin=bin,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    if record_initial_tx and quantity > 0:
        if user is None:
            user = db.scalar(select(User).limit(1))
            if not user:
                user = create_user(db, employee_id="SYSTEM01", role=UserRole.STORE_ADMIN)

        tx = InventoryTransaction(
            part_id=part.id,
            location_id=location.id,
            user_id=user.id,
            transaction_type=TransactionType.RECEIVED,
            quantity_change=quantity,
            quantity_after=quantity,
            notes="Initial stock seeding",
        )
        db.add(tx)
        db.commit()

    return inv


def login_as(client: TestClient, employee_id: str, password: str = "TestPassword123!") -> dict:
    """Helper to authenticate and return Authorization headers."""
    resp = client.post("/api/auth/login", json={"identifier": employee_id, "password": password})
    assert resp.status_code == 200, f"Login failed for {employee_id}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def assert_ledger_invariant(db: Session) -> None:
    """Validate ledger invariant: SUM(quantity_change) == quantity and latest quantity_after == quantity."""
    db.expire_all()
    inventories = db.scalars(select(Inventory)).all()
    for inv in inventories:
        txs = db.scalars(
            select(InventoryTransaction)
            .where(
                InventoryTransaction.part_id == inv.part_id,
                InventoryTransaction.location_id == inv.location_id,
            )
            .order_by(InventoryTransaction.id.asc())
        ).all()
        if not txs:
            assert inv.quantity == 0, f"Inventory {inv.id} has quantity {inv.quantity} but no transactions."
        else:
            total_change = sum(tx.quantity_change for tx in txs)
            assert total_change == inv.quantity, (
                f"Ledger sum invariant failed for part_id={inv.part_id}, location_id={inv.location_id}: "
                f"sum={total_change} != inventory.quantity={inv.quantity}"
            )
            latest_after = txs[-1].quantity_after
            assert latest_after == inv.quantity, (
                f"Ledger quantity_after invariant failed for part_id={inv.part_id}, location_id={inv.location_id}: "
                f"latest_after={latest_after} != inventory.quantity={inv.quantity}"
            )
