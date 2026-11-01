"""CLI tool to import users in bulk from a CSV file.

Usage:
    python -m app.scripts.import_users users.csv [--output results.csv] [--dry-run]
"""
import argparse
import csv
import os
import re
import secrets
import string
import sys
from typing import Dict, List, Set
from sqlalchemy import or_, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.location import Location
from app.models.user import User

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def generate_temp_password(length: int = 18) -> str:
    """Generate a strong random temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    # Ensure at least one upper, one lower, one digit, one special
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%^&*" for c in pw)
        ):
            return pw


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Bulk import users into SpareHub from CSV.")
    parser.add_argument("csv_file", help="Path to input CSV (employee_id,name,email,role,location_code)")
    parser.add_argument("--output", default="imported_users_passwords.csv", help="Path to write generated credentials CSV")
    parser.add_argument("--temp-password-file", help="Optional CSV file mapping employee_id to temporary_password")
    parser.add_argument("--dry-run", action="store_true", help="Validate input and report without committing to database")
    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)
    csv_path = parsed.csv_file

    if not os.path.exists(csv_path):
        print(f"[ERROR] Input CSV file '{csv_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # Optional pre-assigned passwords
    pre_assigned_passwords: Dict[str, str] = {}
    if parsed.temp_password_file:
        if not os.path.exists(parsed.temp_password_file):
            print(f"[ERROR] Temp password file '{parsed.temp_password_file}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(parsed.temp_password_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                emp_id = row.get("employee_id", "").strip().upper()
                pw = row.get("temporary_password", "").strip()
                if emp_id and pw:
                    pre_assigned_passwords[emp_id] = pw

    # Read and parse input CSV
    rows: List[Dict[str, str]] = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"employee_id", "name", "email", "role", "location_code"}
        if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
            print(
                f"[ERROR] CSV must contain columns: {', '.join(sorted(required_cols))}. Found: {reader.fieldnames}",
                file=sys.stderr,
            )
            sys.exit(1)

        for row_idx, r in enumerate(reader, start=2):
            emp_id = (r.get("employee_id") or "").strip().upper()
            name = (r.get("name") or "").strip()
            email = (r.get("email") or "").strip().lower()
            role_str = (r.get("role") or "").strip().upper()
            loc_code = (r.get("location_code") or "").strip().upper()

            rows.append({
                "row_idx": row_idx,
                "employee_id": emp_id,
                "name": name,
                "email": email,
                "role": role_str,
                "location_code": loc_code,
            })

    if not rows:
        print("[ERROR] Input CSV contains no user rows.", file=sys.stderr)
        sys.exit(1)

    # Validate rows & check duplicates within CSV
    errors: List[str] = []
    seen_emp_ids: Set[str] = set()
    seen_emails: Set[str] = set()

    for r in rows:
        idx = r["row_idx"]
        if not r["employee_id"]:
            errors.append(f"Row {idx}: employee_id is required.")
        elif r["employee_id"] in seen_emp_ids:
            errors.append(f"Row {idx}: duplicate employee_id '{r['employee_id']}' in CSV.")
        else:
            seen_emp_ids.add(r["employee_id"])

        if not r["name"]:
            errors.append(f"Row {idx}: name is required.")

        if not r["email"]:
            errors.append(f"Row {idx}: email is required.")
        elif not EMAIL_REGEX.match(r["email"]):
            errors.append(f"Row {idx}: invalid email format '{r['email']}'.")
        elif r["email"] in seen_emails:
            errors.append(f"Row {idx}: duplicate email '{r['email']}' in CSV.")
        else:
            seen_emails.add(r["email"])

        if r["role"] not in {"EMPLOYEE", "STORE_ADMIN"}:
            errors.append(f"Row {idx}: invalid role '{r['role']}'. Must be EMPLOYEE or STORE_ADMIN.")

        if not r["location_code"]:
            errors.append(f"Row {idx}: location_code is required.")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(1)

    # Validate against Database
    db = SessionLocal()
    try:
        # Check locations
        loc_codes = {r["location_code"] for r in rows}
        loc_objs = db.scalars(select(Location).where(Location.code.in_(loc_codes))).all()
        loc_map = {loc.code: loc.id for loc in loc_objs}
        missing_locs = loc_codes - set(loc_map.keys())
        if missing_locs:
            for ml in sorted(missing_locs):
                print(f"[ERROR] Location code '{ml}' does not exist in database.", file=sys.stderr)
            sys.exit(1)

        # Check existing users in DB
        all_emp_ids = list(seen_emp_ids)
        all_emails = list(seen_emails)
        existing_users = db.scalars(
            select(User).where(or_(User.employee_id.in_(all_emp_ids), User.email.in_(all_emails)))
        ).all()

        if existing_users:
            for eu in existing_users:
                if eu.employee_id in seen_emp_ids:
                    print(f"[ERROR] Employee ID '{eu.employee_id}' already exists in database.", file=sys.stderr)
                if eu.email in seen_emails:
                    print(f"[ERROR] Email '{eu.email}' already exists in database.", file=sys.stderr)
            sys.exit(1)

        if parsed.dry_run:
            print(f"[DRY-RUN] Validation succeeded for {len(rows)} users. No changes made.")
            return

        # Single transaction import
        results: List[Dict[str, str]] = []
        for r in rows:
            emp_id = r["employee_id"]
            pw = pre_assigned_passwords.get(emp_id) or generate_temp_password()
            pw_hash = hash_password(pw)
            user = User(
                employee_id=emp_id,
                name=r["name"],
                email=r["email"],
                password_hash=pw_hash,
                role=UserRole(r["role"]),
                location_id=loc_map[r["location_code"]],
                is_active=True,
                failed_login_attempts=0,
                locked_until=None,
            )
            db.add(user)
            results.append({"employee_id": emp_id, "temporary_password": pw})

        db.commit()

        # Write credentials CSV
        out_path = parsed.output
        with open(out_path, mode="w", newline="", encoding="utf-8") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=["employee_id", "temporary_password"])
            writer.writeheader()
            writer.writerows(results)

        # Restrict permissions if POSIX
        try:
            if hasattr(os, "chmod"):
                os.chmod(out_path, 0o600)
        except Exception:
            pass

        print(f"[SUCCESS] Successfully imported {len(rows)} users.")
        print(f"[NOTICE] Passwords written to '{out_path}'. Deliver securely to users.")
        print("[NOTE] Change-password feature on first login is recommended for future iteration.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

