"""Dynamic permissions matrix tests over all registered routes."""
import re
import pytest
from fastapi.routing import APIRoute
from app.main import app
from app.models.enums import UserRole
from tests.conftest import create_location, create_user, login_as

EXEMPT_NO_AUTH_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/health/db"),
    ("POST", "/api/auth/login"),
}


def get_all_api_routes():
    """Extract all distinct (method, path) pairs from app.routes."""
    routes = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                if method not in {"HEAD", "OPTIONS"}:
                    routes.append((method, r.path))
    return sorted(routes)


def format_test_path(path: str) -> str:
    """Replace path parameters like {id} with '1'."""
    return re.sub(r"\{[a-zA-Z0-9_]+\}", "1", path)


ALL_ROUTES = get_all_api_routes()


@pytest.mark.parametrize("method,path", ALL_ROUTES)
def test_all_routes_require_authentication(client, db_session, method, path):
    """Every route except explicit health and login must return 401 without token."""
    test_url = format_test_path(path)
    resp = client.request(method, test_url)

    if (method, path) in EXEMPT_NO_AUTH_ROUTES:
        assert resp.status_code != 401, f"Exempt route {method} {path} should not return 401"
    else:
        assert resp.status_code == 401, f"Route {method} {path} ({test_url}) did not require authentication! Got {resp.status_code}"


@pytest.mark.parametrize("method,path", [r for r in ALL_ROUTES if r[1].startswith("/api/admin/")])
def test_all_admin_routes_forbidden_for_employee(client, db_session, method, path):
    """Every /api/admin/* route must return 403 when called with EMPLOYEE role."""
    loc = create_location(db_session)
    create_user(db_session, employee_id="EMP_PERM", role=UserRole.EMPLOYEE, location=loc)
    headers = login_as(client, "EMP_PERM")

    test_url = format_test_path(path)
    resp = client.request(method, test_url, headers=headers)
    assert resp.status_code == 403, (
        f"Admin route {method} {path} ({test_url}) did not return 403 for employee! Got {resp.status_code}: {resp.text}"
    )


def test_unprotected_routes_whitelist_integrity(client):
    """Verify that no unexpected unprotected routes exist. Fails if a new unprotected route is added."""
    unprotected = set()
    for method, path in ALL_ROUTES:
        test_url = format_test_path(path)
        resp = client.request(method, test_url)
        if resp.status_code != 401:
            unprotected.add((method, path))

    assert unprotected == EXEMPT_NO_AUTH_ROUTES, (
        f"Unprotected routes mismatch! Found unexpected unprotected routes: {unprotected - EXEMPT_NO_AUTH_ROUTES}"
    )

