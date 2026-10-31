"""Module 4 Backend Acceptance Tests (A1 to A9).

Runs all verification checks against /api/admin/locations and /api/admin/machines.
"""
import json
import os
import sys
import urllib.error
import urllib.request

# Insert backend directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE = "http://127.0.0.1:8765"
SEED_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD", "ChangeMeInDev123!")

all_passed = True


def request(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            res_body = r.read().decode("utf-8")
            return r.status, json.loads(res_body) if res_body else None
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        return e.code, json.loads(res_body) if res_body else None


def check(label, condition, detail=""):
    global all_passed
    mark = "[PASS]" if condition else "[FAIL]"
    print(f"  {mark} {label}" + (f": {detail}" if detail else ""))
    if not condition:
        all_passed = False
    return condition


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def cleanup_test_data():
    from app.db.session import SessionLocal
    from app.models.machine import Machine
    from app.models.location import Location
    db = SessionLocal()
    try:
        db.query(Machine).filter(Machine.code.like("TEST_%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.code.like("TEST_%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.name.ilike("%Test Facility Plant 99%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.name == "Different Name Unique").delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  Cleanup notice: {e}")
    finally:
        db.close()


def main():
    global all_passed

    # Pre-clean any test artifacts
    cleanup_test_data()

    # 1. Obtain Tokens
    section("SETUP: Authenticating Test Users")
    status, res = request("POST", "/api/auth/login", {"identifier": "ITCADM001", "password": SEED_PASSWORD})
    assert status == 200, f"Admin login failed: {res}"
    admin_token = res["access_token"]
    print("  Obtained STORE_ADMIN token for ITCADM001")

    status, res = request("POST", "/api/auth/login", {"identifier": "ITC10452", "password": SEED_PASSWORD})
    assert status == 200, f"Employee login failed: {res}"
    emp_token = res["access_token"]
    print("  Obtained EMPLOYEE token for ITC10452")

    # A1. Role Enforcement
    section("A1: Role Enforcement")
    status, res = request("GET", "/api/admin/locations")
    check("Unauthenticated GET /api/admin/locations -> 401", status == 401 and res.get("code") == "not_authenticated", f"got {status} {res}")

    status, res = request("GET", "/api/admin/machines")
    check("Unauthenticated GET /api/admin/machines -> 401", status == 401 and res.get("code") == "not_authenticated", f"got {status} {res}")

    status, res = request("GET", "/api/admin/locations", token=emp_token)
    check("Employee GET /api/admin/locations -> 403 forbidden", status == 403 and res.get("code") == "forbidden", f"got {status} {res}")

    status, res = request("GET", "/api/admin/machines", token=emp_token)
    check("Employee GET /api/admin/machines -> 403 forbidden", status == 403 and res.get("code") == "forbidden", f"got {status} {res}")

    status, res = request("GET", "/api/admin/locations", token=admin_token)
    check("Admin GET /api/admin/locations -> 200 OK", status == 200)

    status, res = request("GET", "/api/admin/machines", token=admin_token)
    check("Admin GET /api/admin/machines -> 200 OK", status == 200)

    # A2. Locations listing & aggregate counts
    section("A2: Locations Listing & Counts")
    status, loc_res = request("GET", "/api/admin/locations", token=admin_token)
    check("Returns paginated envelope", all(k in loc_res for k in ("items", "total", "page", "page_size", "total_pages")), f"keys={list(loc_res.keys())}")
    check("At least 4 seed locations present", loc_res["total"] >= 4)
    item0 = loc_res["items"][0]
    check(
        "Location has user_count, machine_count, stocked_part_count, is_active",
        all(k in item0 for k in ("user_count", "machine_count", "stocked_part_count", "is_active", "code", "name")),
        f"Item fields: {list(item0.keys())}",
    )
    has_users = any(loc["user_count"] > 0 for loc in loc_res["items"])
    has_machines = any(loc["machine_count"] > 0 for loc in loc_res["items"])
    check("Seed locations have non-zero aggregate counts", has_users and has_machines)

    # Find a seed location that has active users or positive inventory
    used_loc = next((loc for loc in loc_res["items"] if loc["user_count"] > 0 or loc["stocked_part_count"] > 0), None)
    assert used_loc is not None, "Could not find a seed location in use"

    # A3. Location Creation & Validation
    section("A3: Location Creation & Validation")
    test_loc_code = "TEST_PLANT_99"
    test_loc_name = "  Test Facility Plant 99  "
    create_payload = {
        "name": test_loc_name,
        "code": "test_plant_99",  # Lowercase to test uppercase normalization
        "city": " Pune ",
    }
    status, created_loc = request("POST", "/api/admin/locations", create_payload, token=admin_token)
    check("POST /api/admin/locations returns 201", status == 201, f"got {status} {created_loc}")
    check("Code normalized to uppercase", created_loc.get("code") == test_loc_code)
    check("Name whitespace trimmed", created_loc.get("name") == "Test Facility Plant 99")
    check("City whitespace trimmed", created_loc.get("city") == "Pune")
    created_loc_id = created_loc.get("id")

    # Duplicate name check
    status, res = request("POST", "/api/admin/locations", {
        "name": "test facility plant 99",
        "code": "TEST_PLANT_DIFF",
        "city": "Pune",
    }, token=admin_token)
    check("Duplicate name -> 409 duplicate_name with field='name'", status == 409 and res.get("code") == "duplicate_name" and res.get("field") == "name", f"got {status} {res}")

    # Duplicate code check
    status, res = request("POST", "/api/admin/locations", {
        "name": "Different Name Unique",
        "code": "TEST_PLANT_99",
        "city": "Pune",
    }, token=admin_token)
    check("Duplicate code -> 409 duplicate_code with field='code'", status == 409 and res.get("code") == "duplicate_code" and res.get("field") == "code", f"got {status} {res}")

    # Invalid code format (special chars)
    status, res = request("POST", "/api/admin/locations", {
        "name": "Special Chars Facility",
        "code": "LOC#INVALID!",
        "city": "Pune",
    }, token=admin_token)
    check("Invalid code format -> 422 with field='code'", status == 422 and res.get("field") == "code", f"got {status} {res}")

    # A4. Location Update
    section("A4: Location Update")
    # Empty body
    status, res = request("PATCH", f"/api/admin/locations/{created_loc_id}", {}, token=admin_token)
    check("Empty update body -> 422 empty_update", status == 422 and res.get("code") == "empty_update", f"got {status} {res}")

    # Valid update
    status, res = request("PATCH", f"/api/admin/locations/{created_loc_id}", {
        "city": "Mumbai",
        "name": "Test Facility Plant 99",  # unchanged name shouldn't trigger duplicate conflict
    }, token=admin_token)
    check("PATCH /api/admin/locations/{id} updates city -> 200", status == 200 and res.get("city") == "Mumbai", f"got {status} {res}")

    # Update code to conflicting code
    status, res = request("PATCH", f"/api/admin/locations/{created_loc_id}", {
        "code": used_loc["code"],  # existing seed code (e.g. BLR)
    }, token=admin_token)
    check("Update to conflicting code -> 409 duplicate_code", status == 409 and res.get("code") == "duplicate_code" and res.get("field") == "code", f"got {status} {res}")

    # A5. Safe Location Deactivation
    section("A5: Safe Location Deactivation")
    # Try deactivating seed location with users or stock
    status, res = request("POST", f"/api/admin/locations/{used_loc['id']}/deactivate", token=admin_token)
    check("Deactivate location with users/stock -> 409 location_in_use", status == 409 and res.get("code") == "location_in_use", f"got {status} {res}")

    # Deactivate clean test location (0 users, 0 stock)
    status, res = request("POST", f"/api/admin/locations/{created_loc_id}/deactivate", token=admin_token)
    check("Deactivate unused location -> 200, is_active=False", status == 200 and res.get("is_active") is False, f"got {status} {res}")

    # Reactivate test location
    status, res = request("POST", f"/api/admin/locations/{created_loc_id}/activate", token=admin_token)
    check("Activate unused location -> 200, is_active=True", status == 200 and res.get("is_active") is True, f"got {status} {res}")

    # A6. Location Dropdown Options
    section("A6: Location Dropdown Options")
    status, res = request("GET", "/api/admin/locations/options", token=admin_token)
    check("GET /api/admin/locations/options -> 200", status == 200 and isinstance(res, list))
    check("Only active locations returned and fields id/name/code present", all("id" in o and "name" in o and "code" in o for o in res))
    # Deactivate test location and verify it disappears from options
    request("POST", f"/api/admin/locations/{created_loc_id}/deactivate", token=admin_token)
    _, res_after = request("GET", "/api/admin/locations/options", token=admin_token)
    check("Deactivated location excluded from options", not any(o["id"] == created_loc_id for o in res_after))
    # Reactivate
    request("POST", f"/api/admin/locations/{created_loc_id}/activate", token=admin_token)

    # A7. Machines Listing & Filters
    section("A7: Machines Listing & Filters")
    status, mc_res = request("GET", "/api/admin/machines", token=admin_token)
    check("Machines listing returns envelope with >= 8 machines", status == 200 and mc_res["total"] >= 8)
    m0 = mc_res["items"][0]
    check("Machine item has part_count, is_active, location", "part_count" in m0 and "is_active" in m0 and "location" in m0)

    # Filter location_id=1
    status, res_loc1 = request("GET", "/api/admin/machines?location_id=1", token=admin_token)
    check("Filter by location_id=1 works", status == 200 and all(m["location"]["id"] == 1 for m in res_loc1["items"]))

    # Search q
    first_machine_name = mc_res["items"][0]["name"]
    query_term = first_machine_name.split()[0]
    status, res_q = request("GET", f"/api/admin/machines?q={query_term}", token=admin_token)
    check(f"Search q='{query_term}' finds machines", status == 200 and len(res_q["items"]) > 0)

    # A8. Machine Creation & Location Assignment
    section("A8: Machine Creation & Location Assignment")
    machine_code = "TEST_MC_99"
    status, created_mc = request("POST", "/api/admin/machines", {
        "name": " Test CNC Milling Unit 99 ",
        "code": "test_mc_99",
        "location_id": created_loc_id,
    }, token=admin_token)
    check("POST /api/admin/machines returns 201", status == 201, f"got {status} {created_mc}")
    check("Machine code normalized to uppercase", created_mc.get("code") == machine_code)
    check("Machine name trimmed", created_mc.get("name") == "Test CNC Milling Unit 99")
    check("Assigned location loaded", created_mc.get("location") is not None and created_mc["location"]["id"] == created_loc_id)
    created_mc_id = created_mc.get("id")

    # Duplicate machine code
    status, res = request("POST", "/api/admin/machines", {
        "name": "Another Machine",
        "code": "TEST_MC_99",
    }, token=admin_token)
    check("Duplicate machine code -> 409 duplicate_code", status == 409 and res.get("code") == "duplicate_code" and res.get("field") == "code", f"got {status} {res}")

    # Invalid location_id (nonexistent)
    status, res = request("POST", "/api/admin/machines", {
        "name": "Machine Invalid Loc",
        "code": "TEST_MC_INV",
        "location_id": 999999,
    }, token=admin_token)
    check("Nonexistent location_id -> 422 invalid_location", status == 422 and res.get("code") == "invalid_location" and res.get("field") == "location_id", f"got {status} {res}")

    # Inactive location assignment
    request("POST", f"/api/admin/locations/{created_loc_id}/deactivate", token=admin_token)
    status, res = request("POST", "/api/admin/machines", {
        "name": "Machine Inactive Loc",
        "code": "TEST_MC_INACT",
        "location_id": created_loc_id,
    }, token=admin_token)
    check("Inactive location_id -> 422 invalid_location", status == 422 and res.get("code") == "invalid_location" and res.get("field") == "location_id", f"got {status} {res}")
    request("POST", f"/api/admin/locations/{created_loc_id}/activate", token=admin_token)

    # A9. Machine Deactivation (Always Allowed)
    section("A9: Machine Deactivation")
    target_mc = mc_res["items"][0]
    target_mc_id = target_mc["id"]

    status, res = request("POST", f"/api/admin/machines/{target_mc_id}/deactivate", token=admin_token)
    check(f"Deactivate machine {target_mc_id} -> 200, is_active=False", status == 200 and res.get("is_active") is False, f"got {status} {res}")

    status, res = request("POST", f"/api/admin/machines/{target_mc_id}/activate", token=admin_token)
    check(f"Activate machine {target_mc_id} -> 200, is_active=True", status == 200 and res.get("is_active") is True, f"got {status} {res}")

    # Cleanup test records
    section("CLEANUP: Removing test machine and location")
    from app.db.session import SessionLocal
    from app.models.machine import Machine
    from app.models.location import Location
    db = SessionLocal()
    try:
        db.query(Machine).filter(Machine.code == machine_code).delete()
        db.query(Location).filter(Location.code == test_loc_code).delete()
        db.commit()
        print("  Cleaned up test machine and test location from DB")
    finally:
        db.close()

    section("SUMMARY")
    if all_passed:
        print("  ALL BACKEND ACCEPTANCE CHECKS PASSED!")
    else:
        print("  SOME CHECKS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
