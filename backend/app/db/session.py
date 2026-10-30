from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Engine with pool_pre_ping to automatically test connections before checkout
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=(not settings.is_production),
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an isolated database session and guaranteeing closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
