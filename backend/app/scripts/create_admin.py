"""CLI tool to create a STORE_ADMIN user without running the seed script.

Usage:
    python -m app.scripts.create_admin --employee-id ADMIN01 --name "Admin User" --email admin@example.com --location-code LOC01
"""
import argparse
import getpass
import re
import sys
from sqlalchemy import or_, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.location import Location
from app.models.user import User

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Create a new STORE_ADMIN user in SpareHub.")
    parser.add_argument("--employee-id", required=True, help="Unique employee ID (e.g. ADM001)")
    parser.add_argument("--name", required=True, help="Full name of the admin")
    parser.add_argument("--email", required=True, help="Unique email address")
    parser.add_argument("--location-code", required=True, help="Location code (e.g. LOC01)")
    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)

    emp_id = parsed.employee_id.strip().upper()
    name = parsed.name.strip()
    email = parsed.email.strip().lower()
    loc_code = parsed.location_code.strip().upper()

    if not emp_id:
        print("[ERROR] Employee ID cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if not name:
        print("[ERROR] Name cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if not EMAIL_REGEX.match(email):
        print(f"[ERROR] Invalid email format: {email}", file=sys.stderr)
        sys.exit(1)

    # Prompt password securely
    password = getpass.getpass("Enter admin password (min 12 characters): ")
    if len(password) < 12:
        print("[ERROR] Password must be at least 12 characters long.", file=sys.stderr)
        sys.exit(1)

    confirm_password = getpass.getpass("Confirm admin password: ")
    if password != confirm_password:
        print("[ERROR] Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        # Check location exists
        location = db.scalar(select(Location).where(Location.code == loc_code))
        if not location:
            print(f"[ERROR] Location with code '{loc_code}' does not exist.", file=sys.stderr)
            sys.exit(1)

        # Check existing user
        existing = db.scalar(
            select(User).where(or_(User.employee_id == emp_id, User.email == email))
        )
        if existing:
            if existing.employee_id == emp_id:
                print(f"[ERROR] User with employee ID '{emp_id}' already exists.", file=sys.stderr)
            else:
                print(f"[ERROR] User with email '{email}' already exists.", file=sys.stderr)
            sys.exit(1)

        pw_hash = hash_password(password)
        new_admin = User(
            employee_id=emp_id,
            name=name,
            email=email,
            password_hash=pw_hash,
            role=UserRole.STORE_ADMIN,
            location_id=location.id,
            is_active=True,
            failed_login_attempts=0,
            locked_until=None,
        )
        db.add(new_admin)
        db.commit()
        print(f"[SUCCESS] Admin user '{emp_id}' ({name}) created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

