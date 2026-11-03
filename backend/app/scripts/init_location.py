"""CLI tool to verify or initialize a store location in the database.

Usage:
    python -m app.scripts.init_location BLR
"""
import sys
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.location import Location


def ensure_location(loc_code: str) -> None:
    clean_code = loc_code.strip().upper()
    if not clean_code:
        print("[ERROR] Location code cannot be empty.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        loc = db.scalar(select(Location).where(Location.code == clean_code))
        if not loc:
            new_loc = Location(
                name=f"ITC {clean_code}",
                code=clean_code,
                city="Main Facility",
                is_active=True,
            )
            db.add(new_loc)
            db.commit()
            print(f"[SUCCESS] Initialized location '{clean_code}'.")
        else:
            print(f"[INFO] Location '{clean_code}' ({loc.name}) confirmed.")
    finally:
        db.close()


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "BLR"
    ensure_location(code)
