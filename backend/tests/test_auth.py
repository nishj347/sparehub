"""Tests for authentication endpoints, tokens, timing mitigation, and user status."""
from datetime import datetime, timedelta, timezone
import pytest
from app.core.jwt import create_access_token
from app.models.enums import UserRole
from tests.conftest import create_location, create_user


def test_login_by_employee_id_case_insensitive(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP100", password="Password123!", location=loc)

    for id_variant in ["EMP100", "emp100", "Emp100"]:
        resp = client.post("/api/auth/login", json={"identifier": id_variant, "password": "Password123!"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["employee_id"] == "EMP100"


def test_login_by_email_case_insensitive(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP101", email="worker@example.com", password="Password123!", location=loc)

    for email_variant in ["worker@example.com", "WORKER@EXAMPLE.COM", "Worker@Example.Com"]:
        resp = client.post("/api/auth/login", json={"identifier": email_variant, "password": "Password123!"})
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == "worker@example.com"


def test_identical_401_for_wrong_password_unknown_user_inactive_user(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="ACTIVE01", password="Password123!", location=loc)
    create_user(db_session, employee_id="INACTIVE01", password="Password123!", is_active=False, location=loc)

    # 1. Wrong password
    resp_wrong_pw = client.post("/api/auth/login", json={"identifier": "ACTIVE01", "password": "WrongPassword!"})
    # 2. Unknown user
    resp_unknown = client.post("/api/auth/login", json={"identifier": "DOES_NOT_EXIST", "password": "WrongPassword!"})
    # 3. Inactive user
    resp_inactive = client.post("/api/auth/login", json={"identifier": "INACTIVE01", "password": "Password123!"})

    assert resp_wrong_pw.status_code == 401
    assert resp_unknown.status_code == 401
    assert resp_inactive.status_code == 401

    body_expected = {"detail": "Invalid credentials", "code": "invalid_credentials"}
    assert resp_wrong_pw.json() == body_expected
    assert resp_unknown.json() == body_expected
    assert resp_inactive.json() == body_expected


def test_token_validation_states(client, db_session):
    loc = create_location(db_session)
    user = create_user(db_session, employee_id="EMP102", location=loc)

    # 1. Missing token
    resp_missing = client.get("/api/auth/me")
    assert resp_missing.status_code == 401
    assert resp_missing.json()["code"] == "not_authenticated"

    # 2. Tampered token
    resp_tampered = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
    assert resp_tampered.status_code == 401
    assert resp_tampered.json()["code"] == "invalid_token"

    # 3. Expired token
    expired_token = create_access_token(
        user_id=user.id,
        expires_delta=timedelta(seconds=-10),
    )
    resp_expired = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_expired.status_code == 401
    assert resp_expired.json()["code"] == "token_expired"


def test_role_and_is_active_read_from_database(client, db_session):
    """Deactivating a user in DB immediately invalidates subsequent requests with existing token."""
    loc = create_location(db_session)
    user = create_user(db_session, employee_id="EMP103", role=UserRole.EMPLOYEE, location=loc)

    # Login to acquire token
    login_resp = client.post("/api/auth/login", json={"identifier": "EMP103", "password": "TestPassword123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify active
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # Deactivate user in DB
    user.is_active = False
    db_session.commit()

    # Next request with same token must fail 401
    me_after_deactivation = client.get("/api/auth/me", headers=headers)
    assert me_after_deactivation.status_code == 401
    assert me_after_deactivation.json()["code"] == "not_authenticated"


def test_auth_me_never_returns_password_hash(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP104", location=loc)

    login_resp = client.post("/api/auth/login", json={"identifier": "EMP104", "password": "TestPassword123!"})
    token = login_resp.json()["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "password" not in data
    assert "password_hash" not in data
    assert "hashed_password" not in data
