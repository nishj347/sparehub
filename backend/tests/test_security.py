"""Tests for security hardening, lockout mechanisms, rate limits, headers, and production invariants."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import pytest
from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip, login_rate_limiter
from app.models.user import User
from tests.conftest import create_location, create_user


def test_login_lockout_after_five_failed_attempts(client, db_session):
    loc = create_location(db_session)
    user = create_user(db_session, employee_id="LOCK_TEST01", password="CorrectPassword123!", location=loc)

    # 4 wrong attempts: each returns 401
    for attempt in range(1, 5):
        resp = client.post("/api/auth/login", json={"identifier": "LOCK_TEST01", "password": "WrongPassword!"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "invalid_credentials"

    # 5th wrong attempt: triggers lockout
    resp_5 = client.post("/api/auth/login", json={"identifier": "LOCK_TEST01", "password": "WrongPassword!"})
    assert resp_5.status_code == 401

    # Database shows user is locked
    db_session.refresh(user)
    assert user.failed_login_attempts >= 5
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(timezone.utc)

    # 6th attempt, even with the CORRECT password, must return 429 too_many_attempts with Retry-After
    resp_locked = client.post("/api/auth/login", json={"identifier": "LOCK_TEST01", "password": "CorrectPassword123!"})
    assert resp_locked.status_code == 429
    assert resp_locked.json()["code"] == "too_many_attempts"
    assert "Retry-After" in resp_locked.headers

    # Simulate lockout window expiration
    user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    # Now login with correct password succeeds and resets counters
    resp_success = client.post("/api/auth/login", json={"identifier": "LOCK_TEST01", "password": "CorrectPassword123!"})
    assert resp_success.status_code == 200
    db_session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_concurrent_wrong_password_attempts_count_correctly(client, db_session):
    """Multiple concurrent failed logins are counted atomically without race conditions."""
    loc = create_location(db_session)
    user = create_user(db_session, employee_id="LOCK_CONCURR", password="CorrectPassword123!", location=loc)

    def fail_attempt(_):
        return client.post("/api/auth/login", json={"identifier": "LOCK_CONCURR", "password": "WrongPassword!"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fail_attempt, i) for i in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for r in results:
        assert r.status_code in {401, 429}

    db_session.refresh(user)
    assert user.failed_login_attempts >= 5
    assert user.locked_until is not None


def test_ip_rate_limiting_returns_429(client, db_session):
    """In-memory IP rate limiter triggers 429 when client exceeds limit."""
    limiter = InMemoryRateLimiter()
    test_ip = "192.168.1.50"

    # Limit to 3 requests per minute
    for _ in range(3):
        limiter.check_rate_limit(test_ip, limit_per_minute=3)

    # 4th request must raise AppHTTPException 429
    with pytest.raises(Exception) as excinfo:
        limiter.check_rate_limit(test_ip, limit_per_minute=3)
    assert excinfo.value.status_code == 429
    assert excinfo.value.code == "too_many_attempts"


def test_security_headers_present_on_api_responses(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    assert resp.headers.get("Cache-Control") == "no-store"
    assert "X-Request-ID" in resp.headers


def test_request_body_size_limit_returns_413(client):
    # Send Content-Length exceeding 8MB (8 * 1024 * 1024 + 1)
    large_size = 9 * 1024 * 1024
    resp = client.post(
        "/api/auth/login",
        headers={"Content-Length": str(large_size)},
        content=b"",
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "request_too_large"


def test_production_mode_configuration_enforcements():
    # 1. Weak / placeholder SECRET_KEY in production
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/sparehub_test",
            APP_ENV="production",
            SECRET_KEY="dev_secret_key_placeholder_change_in_production_min_32_chars",
        )

    # 2. Too short SECRET_KEY in production
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/sparehub_test",
            APP_ENV="production",
            SECRET_KEY="short_key_under_32_chars",
        )

    # 3. Non-HTTPS CORS origin in production without explicit override
    with pytest.raises(ValueError, match="Non-HTTPS CORS origin"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/sparehub_test",
            APP_ENV="production",
            SECRET_KEY="cryptographically_strong_random_prod_signing_token_9876543210",
            SEED_DEFAULT_PASSWORD="",
            CORS_ORIGINS="http://insecure.example.com",
            ALLOW_INSECURE_CORS=False,
        )

    # 4. SEED_DEFAULT_PASSWORD present in production
    with pytest.raises(ValueError, match="SEED_DEFAULT_PASSWORD must not be configured"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/sparehub_test",
            APP_ENV="production",
            SECRET_KEY="cryptographically_strong_random_prod_signing_token_9876543210",
            CORS_ORIGINS="https://secure.example.com",
            SEED_DEFAULT_PASSWORD="SomeSeedPassword123!",
        )
