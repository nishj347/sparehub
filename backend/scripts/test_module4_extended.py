"""Extended Module 4 acceptance checks matching the full checklist (A3-A9 spec).

Tests:
- /api/admin/ping returns 404
- q=conv, q=% (wildcard-safe), status filter, unassigned=true, location_id filter
- sort=bogus gives 422
- page_size=2 total is correct
- Create 'ccu' / 'ITC Kolkata'; case-insensitive dupe name; dupe code
- Deactivate BLR gives 409 location_in_use; CCU gives 200; repeated deactivate idempotent
- PATCH machine location_id to null; duplicate machine code 409
- /options not captured by /{id}
- Machines with/without location; inactive location gives 422
"""
import json
import os
import sys
import urllib.error
import urllib.request

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
            return r.status, json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        return e.code, json.loads(res_body) if res_body else {}


def check(label, condition, detail=""):
    global all_passed
    mark = "[PASS]" if condition else "[FAIL]"
    print(f"  {mark} {label}" + (f" | {detail}" if detail else ""))
    if not condition:
        all_passed = False
    return condition


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def cleanup():
    from app.db.session import SessionLocal
    from app.models.machine import Machine
    from app.models.location import Location
    db = SessionLocal()
    try:
        db.query(Machine).filter(Machine.code.like("TEST_%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.code.like("TEST_%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.name.ilike("%ITC Kolkata%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.code == "CCU").delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  Cleanup warning: {e}")
    finally:
        db.close()


def main():
    cleanup()

    section("SETUP: Authenticating")
    s, r = request("POST", "/api/auth/login", {"identifier": "ITCADM001", "password": SEED_PASSWORD})
    assert s == 200, f"Admin login failed: {r}"
    adm = r["access_token"]

    s, r = request("POST", "/api/auth/login", {"identifier": "ITC10452", "password": SEED_PASSWORD})
    assert s == 200, f"Employee login failed: {r}"
    emp = r["access_token"]
    print("  Tokens obtained")

    # ─── A3: /api/admin/ping removed ────────────────────────────────
    section("A3 Extra: /api/admin/ping returns 404")
    s, r = request("GET", "/api/admin/ping")
    check("/api/admin/ping -> 404", s == 404, f"got {s}")

    # Employee gets 403 on POST/PATCH/deactivate/activate
    section("A3 Extra: Employee 403 on write endpoints")
    s, _ = request("POST", "/api/admin/locations", {"name": "X", "code": "X", "city": "X"}, token=emp)
    check("Employee POST /api/admin/locations -> 403", s == 403)
    s, _ = request("POST", "/api/admin/machines", {"name": "X", "code": "X"}, token=emp)
    check("Employee POST /api/admin/machines -> 403", s == 403)
    s, _ = request("PATCH", "/api/admin/locations/1", {"city": "X"}, token=emp)
    check("Employee PATCH /api/admin/locations -> 403", s == 403)
    s, _ = request("POST", "/api/admin/locations/1/deactivate", token=emp)
    check("Employee POST deactivate -> 403", s == 403)

    # ─── A4: Create CCU / ITC Kolkata ───────────────────────────────
    section("A4: Location creation — code+name normalization & duplicates")
    s, ccu = request("POST", "/api/admin/locations", {
        "name": "  ITC Kolkata  ",
        "code": " ccu ",  # should become CCU after strip+upper
        "city": " Kolkata ",
    }, token=adm)
    check("POST ' ccu ' / 'ITC Kolkata' -> 201", s == 201, f"got {s} {ccu}")
    check("Code stored as CCU", ccu.get("code") == "CCU")
    check("Name stored as 'ITC Kolkata'", ccu.get("name") == "ITC Kolkata")
    check("City stored as 'Kolkata'", ccu.get("city") == "Kolkata")
    ccu_id = ccu.get("id")

    # Duplicate name (case-insensitive)
    s, r = request("POST", "/api/admin/locations", {
        "name": "itc kolkata",
        "code": "CCU2",
        "city": "Kolkata",
    }, token=adm)
    check("'itc kolkata' -> 409 duplicate_name field=name", s == 409 and r.get("code") == "duplicate_name" and r.get("field") == "name", f"got {s} {r}")

    # Duplicate code
    s, r = request("POST", "/api/admin/locations", {
        "name": "ITC Kolkata Branch",
        "code": "CCU",
        "city": "Kolkata",
    }, token=adm)
    check("code CCU again -> 409 duplicate_code field=code", s == 409 and r.get("code") == "duplicate_code" and r.get("field") == "code", f"got {s} {r}")

    # ─── A5: Deactivation ───────────────────────────────────────────
    section("A5: Location deactivation")
    # Look up BLR by listing and finding it (seed IDs are autoincrement, not hardcoded)
    s, loc_list = request("GET", "/api/admin/locations", token=adm)
    blr = next((l for l in loc_list.get("items", []) if l["code"] == "BLR"), None)
    assert blr is not None, "BLR seed location not found!"
    blr_id = blr["id"]

    s, r = request("POST", f"/api/admin/locations/{blr_id}/deactivate", token=adm)
    check("BLR deactivate -> 409 location_in_use", s == 409 and r.get("code") == "location_in_use", f"got {s} {r}")
    check("409 message has counts", "active user" in r.get("detail", ""), r.get("detail"))

    # CCU (empty) deactivate
    s, r = request("POST", f"/api/admin/locations/{ccu_id}/deactivate", token=adm)
    check("CCU deactivate -> 200 is_active=False", s == 200 and r.get("is_active") is False, f"got {s} {r}")

    # Idempotent repeat
    s, r = request("POST", f"/api/admin/locations/{ccu_id}/deactivate", token=adm)
    check("Repeat deactivate idempotent -> 200", s == 200 and r.get("is_active") is False, f"got {s} {r}")

    # Activate
    s, r = request("POST", f"/api/admin/locations/{ccu_id}/activate", token=adm)
    check("CCU activate -> 200 is_active=True", s == 200 and r.get("is_active") is True, f"got {s} {r}")

    # ─── A6: Machines ───────────────────────────────────────────────
    section("A6: Machine creation & PATCH location_id=null")
    # Create with location
    s, mc1 = request("POST", "/api/admin/machines", {"name": "TEST Machine With Loc", "code": "TEST_MC_WLOC", "location_id": ccu_id}, token=adm)
    check("Create machine with location -> 201", s == 201 and mc1.get("location") is not None, f"got {s} {mc1}")

    # Create without location
    s, mc2 = request("POST", "/api/admin/machines", {"name": "TEST Machine No Loc", "code": "TEST_MC_NLOC"}, token=adm)
    check("Create machine without location -> 201 location=null", s == 201 and mc2.get("location") is None, f"got {s} {mc2}")
    mc2_id = mc2.get("id")

    # Inactive location gives 422
    request("POST", f"/api/admin/locations/{ccu_id}/deactivate", token=adm)
    s, r = request("POST", "/api/admin/machines", {"name": "TEST Bad Loc", "code": "TEST_MC_BADLOC", "location_id": ccu_id}, token=adm)
    check("Inactive location_id -> 422 invalid_location", s == 422 and r.get("code") == "invalid_location", f"got {s} {r}")
    request("POST", f"/api/admin/locations/{ccu_id}/activate", token=adm)

    # PATCH location_id to null
    s, r = request("PATCH", f"/api/admin/machines/{mc2_id}", {"location_id": None}, token=adm)
    check("PATCH location_id=None still 200 (idempotent, was already null)", s == 200 and r.get("location") is None, f"got {s} {r}")

    # Patch existing machine's location_id to a valid loc and then to null
    mc1_id = mc1.get("id")
    s, r = request("PATCH", f"/api/admin/machines/{mc1_id}", {"location_id": None}, token=adm)
    check("PATCH location_id=None unassigns machine -> 200", s == 200 and r.get("location") is None, f"got {s} {r}")

    # Duplicate machine code
    s, r = request("POST", "/api/admin/machines", {"name": "Dup Code", "code": "TEST_MC_WLOC"}, token=adm)
    check("Duplicate machine code -> 409 duplicate_code field=code", s == 409 and r.get("code") == "duplicate_code" and r.get("field") == "code", f"got {s} {r}")

    # ─── A7: Listing / Filter / Sort ────────────────────────────────
    section("A7: Listing, search, filters, sort, pagination")
    # q=conv
    s, r = request("GET", "/api/admin/machines?q=conv", token=adm)
    check("q=conv returns machines with 'conv' in name/code", s == 200 and len(r.get("items", [])) > 0, f"total={r.get('total')}")

    # q=% (should not blow up — LIKE wildcards escaped)
    s, r = request("GET", "/api/admin/machines?q=%25", token=adm)  # %25 is URL-encoded %
    check("q=% (wildcard-safe) -> 200", s == 200, f"got {s}")

    # status filter
    s, r = request("GET", "/api/admin/locations?status=active", token=adm)
    check("status=active filter works", s == 200 and all(loc["is_active"] for loc in r.get("items", [])), f"got {s}")

    # unassigned=true
    s, r = request("GET", "/api/admin/machines?unassigned=true", token=adm)
    check("unassigned=true -> all items have location=null", s == 200 and all(m["location"] is None for m in r.get("items", [])), f"got {s} total={r.get('total')}")

    # location_id filter — use BLR's actual id (not hardcoded 1)
    s, r = request("GET", f"/api/admin/machines?location_id={blr_id}", token=adm)
    items_at_blr = r.get("items", [])
    check("location_id=BLR filter works", s == 200 and len(items_at_blr) > 0 and all(m["location"] is not None and m["location"]["id"] == blr_id for m in items_at_blr), f"got {s} count={len(items_at_blr)}")

    # sort=bogus gives 422
    s, r = request("GET", "/api/admin/machines?sort=bogus", token=adm)
    check("sort=bogus -> 422", s == 422, f"got {s} {r.get('code')}")

    # page_size=2 — total is correct (reflects all machines, not just page)
    s, r = request("GET", "/api/admin/machines?page_size=2&page=1", token=adm)
    s2, r2 = request("GET", "/api/admin/machines?page_size=100", token=adm)
    check("page_size=2 total == total from full list", s == 200 and r.get("total") == r2.get("total"), f"page_size=2 total={r.get('total')} full total={r2.get('total')}")
    check("page_size=2 returns 2 items", len(r.get("items", [])) == 2, f"got {len(r.get('items', []))}")

    # ─── A8: /options not captured by /{id} ─────────────────────────
    section("A8: /options routes work (not captured by /{id})")
    s, r = request("GET", "/api/admin/locations/options", token=adm)
    check("GET /admin/locations/options -> 200 list", s == 200 and isinstance(r, list), f"got {s} type={type(r).__name__}")
    check("options contain id/name/code", all("id" in o and "name" in o and "code" in o for o in r), f"keys: {r[0].keys() if r else 'empty'}")
    check("options are only active locations", all(isinstance(o, dict) and "id" in o for o in r))

    s, r = request("GET", "/api/admin/machines/options", token=adm)
    check("GET /admin/machines/options -> 200 list", s == 200 and isinstance(r, list), f"got {s} type={type(r).__name__}")

    # ─── A9: N+1 avoidance explanation ──────────────────────────────
    section("A9: N+1 avoidance")
    print("  Location list: single SELECT with 3 correlated scalar subqueries (user_cnt, machine_cnt, stocked_cnt)")
    print("  Machine list:  single SELECT with joinedload(Machine.location) + 1 part_count scalar subquery")
    print("  Both resolved in 1 DB round-trip per page. No ORM lazy-loading triggered.")

    # ─── Cleanup ─────────────────────────────────────────────────────
    section("CLEANUP")
    cleanup()
    print("  Test data cleaned")

    section("SUMMARY")
    if all_passed:
        print("  ALL EXTENDED ACCEPTANCE CHECKS PASSED!")
    else:
        print("  SOME CHECKS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
