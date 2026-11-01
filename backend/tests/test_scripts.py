"""Tests for administrative CLI tooling: create_admin and import_users."""
import csv
import getpass
import os
import tempfile
import pytest
from app.models.enums import UserRole
from app.models.user import User
from app.scripts import create_admin, import_users
from tests.conftest import create_location


def test_create_admin_script_execution_and_login(client, db_session, monkeypatch):
    from tests.conftest import TestingSessionLocal
    monkeypatch.setattr(create_admin, "SessionLocal", TestingSessionLocal)
    loc = create_location(db_session, code="LOC_ADMIN_CLI")

    # Mock getpass so it doesn't wait for interactive input
    monkeypatch.setattr(getpass, "getpass", lambda prompt: "AdminPass12345!")

    args = [
        "--employee-id", "ADM_CLI_99",
        "--name", "CLI Administrator",
        "--email", "admin_cli@example.com",
        "--location-code", "LOC_ADMIN_CLI",
    ]
    create_admin.main(args)

    # Verify admin in DB
    db_session.expire_all()
    created = db_session.query(User).filter_by(employee_id="ADM_CLI_99").first()
    assert created is not None
    assert created.role == UserRole.STORE_ADMIN
    assert created.email == "admin_cli@example.com"

    # Verify login works
    resp = client.post("/api/auth/login", json={"identifier": "ADM_CLI_99", "password": "AdminPass12345!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_import_users_dry_run_and_commit(client, db_session, monkeypatch):
    from tests.conftest import TestingSessionLocal
    monkeypatch.setattr(import_users, "SessionLocal", TestingSessionLocal)
    loc = create_location(db_session, code="LOC_IMPORT")

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = os.path.join(tmpdir, "valid_users.csv")
        out_file = os.path.join(tmpdir, "passwords.csv")

        with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["employee_id", "name", "email", "role", "location_code"])
            writer.writerow(["IMP_EMP01", "Imported User One", "imp1@example.com", "EMPLOYEE", "LOC_IMPORT"])
            writer.writerow(["IMP_ADM01", "Imported Admin One", "imp2@example.com", "STORE_ADMIN", "LOC_IMPORT"])

        # 1. Dry run
        import_users.main([csv_file, "--dry-run"])
        db_session.expire_all()
        # No users in DB
        assert db_session.query(User).filter(User.employee_id.in_(["IMP_EMP01", "IMP_ADM01"])).count() == 0

        # 2. Real import
        import_users.main([csv_file, "--output", out_file])
        db_session.expire_all()

        # Users committed to DB
        assert db_session.query(User).filter(User.employee_id.in_(["IMP_EMP01", "IMP_ADM01"])).count() == 2

        # Passwords file generated
        assert os.path.exists(out_file)
        with open(out_file, mode="r", encoding="utf-8") as pf:
            rows = list(csv.DictReader(pf))
            assert len(rows) == 2
            emp_pw_map = {r["employee_id"]: r["temporary_password"] for r in rows}

        # Verify login with generated temporary passwords
        resp1 = client.post("/api/auth/login", json={"identifier": "IMP_EMP01", "password": emp_pw_map["IMP_EMP01"]})
        assert resp1.status_code == 200

        resp2 = client.post("/api/auth/login", json={"identifier": "IMP_ADM01", "password": emp_pw_map["IMP_ADM01"]})
        assert resp2.status_code == 200


def test_import_users_all_or_nothing_on_invalid_row(client, db_session, monkeypatch):
    from tests.conftest import TestingSessionLocal
    monkeypatch.setattr(import_users, "SessionLocal", TestingSessionLocal)
    create_location(db_session, code="LOC_ALL_NOTHING")

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = os.path.join(tmpdir, "bad_users.csv")
        with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["employee_id", "name", "email", "role", "location_code"])
            writer.writerow(["IMP_GOOD", "Valid User", "valid@example.com", "EMPLOYEE", "LOC_ALL_NOTHING"])
            # Second row has bad email
            writer.writerow(["IMP_BAD", "Invalid User", "not-an-email", "EMPLOYEE", "LOC_ALL_NOTHING"])

        with pytest.raises(SystemExit):
            import_users.main([csv_file])

        # Ensure atomic rollback / no partial commits: IMP_GOOD must NOT exist
        assert db_session.query(User).filter_by(employee_id="IMP_GOOD").first() is None
