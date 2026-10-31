"""Acceptance test script for Module 3 authentication endpoints.

Run with:  python scripts/test_auth.py   (from the backend/ directory)
"""
import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE = "http://127.0.0.1:8765"
SEED_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD", "ChangeMeInDev123!")

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path, token=None):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Accept": "application/json"},
        method="GET"
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def check(label, condition, detail=""):
    global all_passed
    mark = "[PASS]" if condition else "[FAIL]"
    print(f"  {mark} {label}" + (f": {detail}" if detail else ""))
    if not condition:
        print(f"    Expected True but got False")
        all_passed = False
    return condition


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

all_passed = True

# --- Test 1: Login variations -------------------------------------------------
section("1. POST /api/auth/login - various identifier forms")

status, body = post("/api/auth/login", {"identifier": "ITCADM001", "password": SEED_PASSWORD})
check("Admin login by employee ID (uppercase)", status == 200, f"status={status}")
check("Response has access_token", "access_token" in body)
check("Response has user.role=STORE_ADMIN", body.get("user", {}).get("role") == "STORE_ADMIN")
check("No password_hash in user", "password_hash" not in body.get("user", {}))
admin_token = body.get("access_token", "")

status, body = post("/api/auth/login", {"identifier": "itcadm001", "password": SEED_PASSWORD})
check("Admin login by employee ID (lowercase)", status == 200, f"status={status}")

status, body = post("/api/auth/login", {"identifier": "rajesh.sharma@example-itc.test", "password": SEED_PASSWORD})
check("Admin login by email", status == 200, f"status={status}")

status, body = post("/api/auth/login", {"identifier": "ITC10452", "password": SEED_PASSWORD})
check("Employee login", status == 200, f"status={status}")
emp_token = body.get("access_token", "")
check("Employee role is EMPLOYEE", body.get("user", {}).get("role") == "EMPLOYEE")
check("User has location", "location" in body.get("user", {}))

# --- Test 2: Login failures (all must return identical 401) -------------------
section("2. Login failures - uniform 401 response")

s1, b1 = post("/api/auth/login", {"identifier": "ITCADM001", "password": "wrongpassword"})
s2, b2 = post("/api/auth/login", {"identifier": "DOES_NOT_EXIST", "password": SEED_PASSWORD})
check("Wrong password -> 401", s1 == 401, f"status={s1}")
check("Unknown user -> 401", s2 == 401, f"status={s2}")

check("Wrong password code=invalid_credentials", b1.get("code") == "invalid_credentials")
check("Unknown user code=invalid_credentials", b2.get("code") == "invalid_credentials")
check("Both responses have same detail", b1.get("detail") == b2.get("detail"), b1.get("detail"))

# Inactive user test by temporarily deactivating and restoring afterwards
from app.db.session import SessionLocal
from sqlalchemy import select
from app.models.user import User

db = SessionLocal()
try:
    user = db.scalar(select(User).where(User.employee_id == "ITC10452"))
    user.is_active = False
    db.commit()

    s3, b3 = post("/api/auth/login", {"identifier": "ITC10452", "password": SEED_PASSWORD})
    check("Inactive user -> 401", s3 == 401, f"status={s3}")
    check("Inactive code=invalid_credentials", b3.get("code") == "invalid_credentials")
    check("All 3 error responses identical detail", b1["detail"] == b2["detail"] == b3["detail"])
finally:
    user = db.scalar(select(User).where(User.employee_id == "ITC10452"))
    user.is_active = True
    db.commit()
    db.close()


# --- Test 3: GET /api/auth/me --------------------------------------------------
section("3. GET /api/auth/me - token validation")

s, b = get("/api/auth/me", token=admin_token)
check("Valid token -> 200", s == 200, f"status={s}")
check("Returns employee_id", "employee_id" in b)
check("No password_hash", "password_hash" not in b)
check("Has location.code", b.get("location", {}).get("code") == "BLR")

s, b = get("/api/auth/me")
check("No token -> 401 not_authenticated", s == 401 and b.get("code") == "not_authenticated", f"code={b.get('code')}")

s, b = get("/api/auth/me", token="eyJhbGciOiJIUzI1NiJ9.tampered.invalid")
check("Tampered token -> 401 invalid_token", s == 401 and b.get("code") == "invalid_token", f"code={b.get('code')}")

# Generate expired token
import jwt as pyjwt
from app.core.config import get_settings
settings = get_settings()
now = datetime.now(timezone.utc)
expired_payload = {"sub": "1", "iat": int((now - timedelta(hours=2)).timestamp()), "exp": int((now - timedelta(hours=1)).timestamp())}
expired_token = pyjwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
s, b = get("/api/auth/me", token=expired_token)
check("Expired token -> 401 token_expired", s == 401 and b.get("code") == "token_expired", f"code={b.get('code')}")

# --- Test 4: GET /api/admin/ping - role enforcement --------------------------
section("4. GET /api/admin/ping - STORE_ADMIN only")

s, b = get("/api/admin/ping", token=admin_token)
check("Admin token -> 200 ok", s == 200 and b.get("status") == "ok", f"status={s} body={b}")
check("Admin ping role field", b.get("role") == "STORE_ADMIN")

s, b = get("/api/admin/ping", token=emp_token)
check("Employee token -> 403 forbidden", s == 403 and b.get("code") == "forbidden", f"code={b.get('code')}")

s, b = get("/api/admin/ping")
check("No token -> 401", s == 401, f"status={s}")

# --- Test 5: Health endpoints still public ------------------------------------
section("5. Health endpoints - no auth required")

s, b = get("/api/health")
check("GET /api/health -> 200", s == 200 and b.get("status") == "ok")
s, b = get("/api/health/db")
check("GET /api/health/db -> 200", s == 200 and b.get("status") == "ok")


print(f"\n{'='*60}")
print("  All acceptance tests completed.")
print(f"{'='*60}\n")

if not all_passed:
    sys.exit(1)


