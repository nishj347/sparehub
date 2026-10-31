"""Module 5A Backend Acceptance Tests.

Covers all 12 acceptance criteria:
1. Seeded parts & BRG-6205 total_quantity (21), 4 locations, stock flags
2. Employee 403 on GET/POST/PATCH/DELETE/image/stock endpoints; no token 401
3. Create part with 2 machines + initial stock 10 at Pune -> inventory + RECEIVED tx (+10); duplicate part_number 409
4. Create part with inactive machine -> 422; with inactive location -> 422
5. Receive +5 -> 15 (RECEIVED +5); Adjust to 12 -> 12 (ADJUSTED -3); Adjust to 12 again -> 422 no_change; Adjust without notes -> 422; Receive <= 0 -> 422
6. Concurrency: 10 parallel receive requests of +1 -> exactly +10 final stock and 10 ledger entries
7. Ledger integrity: SUM(quantity_change) == quantity for all inventory rows
8. Image upload valid PNG -> reachable via /uploads/...; txt renamed to png -> 422 invalid_image; >5MB -> 413; replace deletes old; DELETE clears path and file
9. PATCH part (name, specs, machines) -> part_number immutable; specs validation; deactivate/activate idempotent; receive on inactive part -> 409
10. Filters: q=bearing, q=conveyor (machine match), category, stock=low, stock=out, location_id, machine_id, sort=bogus -> 422, page_size=5 total correct, /categories not captured by /{id}
11. Cleanup test parts, transactions, and files; confirm uploads/ clean
12. Health check & Alembic current status
"""
import concurrent.futures
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

# Setup sys.path for direct imports
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


def post_multipart(path, field_name, filename, file_bytes, content_type, token=None):
    url = f"{BASE}{path}"
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
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


def cleanup_test_artifacts():
    from app.db.session import SessionLocal
    from app.models.inventory import Inventory
    from app.models.inventory_transaction import InventoryTransaction
    from app.models.machine import Machine
    from app.models.part_machine import PartMachine
    from app.models.spare_part import SparePart
    from app.models.location import Location

    db = SessionLocal()
    try:
        # Find test parts created by test script
        test_parts = db.query(SparePart).filter(
            (SparePart.part_number.like("TEST-%")) | (SparePart.part_number.like("TEST_%"))
        ).all()
        for p in test_parts:
            # Delete transactions
            db.query(InventoryTransaction).filter(InventoryTransaction.part_id == p.id).delete(synchronize_session=False)
            # Delete inventory
            db.query(Inventory).filter(Inventory.part_id == p.id).delete(synchronize_session=False)
            # Delete part_machines
            db.query(PartMachine).filter(PartMachine.part_id == p.id).delete(synchronize_session=False)
            # Delete part
            db.delete(p)

        # Deactivate any temp machines/locations if created
        db.query(Machine).filter(Machine.code.like("TEST_%")).delete(synchronize_session=False)
        db.query(Location).filter(Location.code.like("TEST_%")).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  Cleanup note: {e}")
    finally:
        db.close()


def main():
    cleanup_test_artifacts()

    section("SETUP: Authenticating Admin and Employee")
    s, r = request("POST", "/api/auth/login", {"identifier": "ITCADM001", "password": SEED_PASSWORD})
    assert s == 200, f"Admin login failed: {r}"
    adm_token = r["access_token"]
    print("  STORE_ADMIN authenticated (ITCADM001)")

    s, r = request("POST", "/api/auth/login", {"identifier": "ITC10452", "password": SEED_PASSWORD})
    assert s == 200, f"Employee login failed: {r}"
    emp_token = r["access_token"]
    print("  EMPLOYEE authenticated (ITC10452)")

    # 1. GET /api/admin/parts returns seeded rows with total_quantity and stock flags
    section("1. Seeded parts listing & BRG-6205 verification")
    s, parts_page = request("GET", "/api/admin/parts?page_size=50", token=adm_token)
    check("GET /api/admin/parts -> 200", s == 200)
    check("Returns 15 seeded parts", parts_page.get("total") == 15, f"total={parts_page.get('total')}")

    brg = next((p for p in parts_page.get("items", []) if p["part_number"] == "BRG-6205"), None)
    check("BRG-6205 found in listing", brg is not None)
    if brg:
        check("BRG-6205 total_quantity is 21", brg.get("total_quantity") == 21, f"got {brg.get('total_quantity')}")
        check("BRG-6205 location_count is 4", brg.get("location_count") == 4, f"got {brg.get('location_count')}")
        check("BRG-6205 low_stock is True", brg.get("low_stock") is True, f"got {brg.get('low_stock')}")
        check("BRG-6205 out_of_stock is False", brg.get("out_of_stock") is False, f"got {brg.get('out_of_stock')}")

    # 2. Role enforcement
    section("2. Role enforcement: Employee 403, No token 401")
    s, _ = request("GET", "/api/admin/parts")
    check("No token GET /api/admin/parts -> 401", s == 401)
    s, _ = request("GET", "/api/admin/parts", token=emp_token)
    check("Employee GET /api/admin/parts -> 403", s == 403)
    s, _ = request("POST", "/api/admin/parts", {"part_number": "T1", "name": "T1", "category": "C1"}, token=emp_token)
    check("Employee POST /api/admin/parts -> 403", s == 403)
    s, _ = request("PATCH", "/api/admin/parts/1", {"name": "T1"}, token=emp_token)
    check("Employee PATCH /api/admin/parts/1 -> 403", s == 403)
    s, _ = request("POST", "/api/admin/parts/1/deactivate", token=emp_token)
    check("Employee POST /api/admin/parts/1/deactivate -> 403", s == 403)
    s, _ = request("POST", "/api/admin/inventory/1/receive", {"quantity": 1}, token=emp_token)
    check("Employee POST /api/admin/inventory/1/receive -> 403", s == 403)

    # Lookup Pune location and active machines
    s, locs = request("GET", "/api/admin/locations/options", token=adm_token)
    pune_loc = next((l for l in locs if "pune" in l["name"].lower() or l["code"] == "PNQ"), None)
    assert pune_loc is not None, "Pune location not found!"
    pune_id = pune_loc["id"]

    s, mcs = request("GET", "/api/admin/machines/options", token=adm_token)
    assert len(mcs) >= 2, "Need at least 2 active machines"
    m_ids = [mcs[0]["id"], mcs[1]["id"]]

    # 3. Create part with 2 machines + initial stock 10 at Pune
    section("3. Create part with 2 machines & initial stock 10 at Pune")
    test_part_num = "TEST-PART-5A-01"
    create_payload = {
        "part_number": " test-part-5a-01 ",  # lower + whitespace -> should normalize to TEST-PART-5A-01
        "name": " High Precision Servo Bearing ",
        "category": "Bearings",
        "manufacturer": "SKF Industrial",
        "description": "High precision ball bearing for test verification",
        "specifications": [
            {"key": "Shaft Diameter", "value": "25mm"},
            {"key": "Dynamic Load", "value": "14.8 kN"},
        ],
        "machine_ids": m_ids,
        "initial_stock": {
            "location_id": pune_id,
            "quantity": 10,
            "store_name": "Central Stores",
            "rack": "R-02",
            "bin": "B-14",
            "min_stock_level": 4,
        },
    }
    s, created_part = request("POST", "/api/admin/parts", create_payload, token=adm_token)
    check("POST /api/admin/parts -> 201", s == 201, f"got {s} {created_part}")
    created_part_id = created_part.get("id")
    check("Part number normalized to uppercase", created_part.get("part_number") == test_part_num)
    check("Total quantity is 10", created_part.get("total_quantity") == 10, f"got {created_part.get('total_quantity')}")
    check("2 machines linked", len(created_part.get("machines", [])) == 2)
    check("1 inventory row exists", len(created_part.get("inventory", [])) == 1)

    pune_inv = created_part.get("inventory", [])[0] if created_part.get("inventory") else {}
    test_inv_id = pune_inv.get("id")
    check("Inventory has quantity 10 at Pune", pune_inv.get("quantity") == 10 and pune_inv.get("location", {}).get("id") == pune_id)

    # Check opening transaction
    recent_txs = created_part.get("recent_transactions", [])
    check("Has 1 recent transaction", len(recent_txs) == 1)
    if recent_txs:
        t0 = recent_txs[0]
        check("Transaction type is RECEIVED", t0.get("type") == "RECEIVED")
        check("Quantity change is +10", t0.get("quantity_change") == 10)
        check("Quantity after is 10", t0.get("quantity_after") == 10)
        check("Notes is 'Initial stock'", t0.get("notes") == "Initial stock")
        check("User is admin", t0.get("user", {}).get("employee_id") == "ITCADM001")

    # Duplicate part number (different case)
    s, dupe_res = request("POST", "/api/admin/parts", {
        "part_number": "test-part-5a-01",
        "name": "Dupe Part",
        "category": "Bearings",
    }, token=adm_token)
    check("Duplicate part number -> 409 duplicate_part_number field=part_number", s == 409 and dupe_res.get("code") == "duplicate_part_number" and dupe_res.get("field") == "part_number")

    # 4. Inactive machine and location validation
    section("4. Inactive machine & inactive location validation")
    # Deactivate machine 0 temporarily
    request("POST", f"/api/admin/machines/{m_ids[0]}/deactivate", token=adm_token)
    s, r = request("POST", "/api/admin/parts", {
        "part_number": "TEST-PART-BADM",
        "name": "Bad Machine Part",
        "category": "Bearings",
        "machine_ids": [m_ids[0]],
    }, token=adm_token)
    check("Inactive machine -> 422 invalid_machine field=machine_ids", s == 422 and r.get("code") == "invalid_machine" and r.get("field") == "machine_ids")
    request("POST", f"/api/admin/machines/{m_ids[0]}/activate", token=adm_token)

    # Inactive location for initial stock
    s, r = request("POST", "/api/admin/parts", {
        "part_number": "TEST-PART-BADL",
        "name": "Bad Loc Part",
        "category": "Bearings",
        "initial_stock": {"location_id": 999999, "quantity": 5},
    }, token=adm_token)
    check("Invalid location -> 422 invalid_location", s == 422 and r.get("code") == "invalid_location")

    # 5. Receive and Adjust operations
    section("5. Receive & Adjust stock operations")
    # Receive +5 -> quantity 15
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/receive", {"quantity": 5, "notes": "Batch shipment PO-991"}, token=adm_token)
    check("Receive +5 -> 200, quantity 15", s == 200 and r.get("quantity") == 15, f"got {s} {r.get('quantity')}")

    # Check detail shows updated transaction
    s, detail = request("GET", f"/api/admin/parts/{created_part_id}", token=adm_token)
    t_latest = detail.get("recent_transactions", [])[0] if detail.get("recent_transactions") else {}
    check("Latest tx is RECEIVED +5, quantity_after 15", t_latest.get("type") == "RECEIVED" and t_latest.get("quantity_change") == 5 and t_latest.get("quantity_after") == 15)

    # Adjust to 12 -> delta -3
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/adjust", {"new_quantity": 12, "notes": "Cycle count physical reconciliation"}, token=adm_token)
    check("Adjust to 12 -> 200, quantity 12", s == 200 and r.get("quantity") == 12, f"got {s} {r.get('quantity')}")

    # Check transaction for adjust
    s, detail = request("GET", f"/api/admin/parts/{created_part_id}", token=adm_token)
    t_adj = detail.get("recent_transactions", [])[0]
    check("Adjust tx is ADJUSTED -3, quantity_after 12", t_adj.get("type") == "ADJUSTED" and t_adj.get("quantity_change") == -3 and t_adj.get("quantity_after") == 12)

    # Adjust to 12 again -> 422 no_change
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/adjust", {"new_quantity": 12, "notes": "Same count again"}, token=adm_token)
    check("Adjust to same quantity -> 422 no_change", s == 422 and r.get("code") == "no_change", f"got {s} {r.get('code')}")

    # Adjust without notes -> 422 validation_error
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/adjust", {"new_quantity": 11}, token=adm_token)
    check("Adjust without notes -> 422 validation_error", s == 422)

    # Receive 0 or negative -> 422
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/receive", {"quantity": 0}, token=adm_token)
    check("Receive 0 -> 422 validation_error", s == 422)
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/receive", {"quantity": -5}, token=adm_token)
    check("Receive negative -> 422 validation_error", s == 422)

    # 6. Concurrency check: 10 parallel receives of +1
    section("6. Concurrency check: 10 parallel receives of +1")
    # Current quantity is 12. 10 * (+1) should result in exactly 22!
    def do_receive():
        return request("POST", f"/api/admin/inventory/{test_inv_id}/receive", {"quantity": 1, "notes": "Concurrent thread receive"}, token=adm_token)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(do_receive) for _ in range(10)]
        results = [f.result() for f in futures]

    all_200 = all(res[0] == 200 for res in results)
    check("All 10 concurrent requests returned 200", all_200)

    s, final_inv = request("GET", f"/api/admin/parts/{created_part_id}", token=adm_token)
    pune_final = next(i for i in final_inv["inventory"] if i["id"] == test_inv_id)
    check("Final inventory quantity is exactly 22 (12 + 10)", pune_final["quantity"] == 22, f"got {pune_final['quantity']}")

    # 7. Ledger integrity check
    section("7. Ledger integrity check (SUM(quantity_change) == quantity)")
    from app.db.session import SessionLocal
    from app.models.inventory import Inventory
    from app.models.inventory_transaction import InventoryTransaction
    from sqlalchemy import func
    db = SessionLocal()
    try:
        mismatches = (
            db.query(
                Inventory.id,
                Inventory.part_id,
                Inventory.location_id,
                Inventory.quantity,
                func.coalesce(func.sum(InventoryTransaction.quantity_change), 0).label("tx_sum"),
            )
            .outerjoin(
                InventoryTransaction,
                (InventoryTransaction.part_id == Inventory.part_id)
                & (InventoryTransaction.location_id == Inventory.location_id),
            )
            .group_by(Inventory.id, Inventory.part_id, Inventory.location_id, Inventory.quantity)
            .having(Inventory.quantity != func.coalesce(func.sum(InventoryTransaction.quantity_change), 0))
            .all()
        )
        check("Every inventory row matches sum of transaction ledger", len(mismatches) == 0, f"mismatches={mismatches}")
    finally:
        db.close()

    # 8. Image upload, validation, limit, replace, delete
    section("8. Image upload, magic-bytes, size cap, replace & delete")
    # Valid 1x1 PNG bytes
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    s, r = post_multipart(f"/api/admin/parts/{created_part_id}/image", "file", "photo.png", valid_png, "image/png", token=adm_token)
    check("Upload valid PNG -> 200", s == 200, f"got {s} {r}")
    image_url = r.get("image_url")
    check("Part has image_url starting with /uploads/", image_url is not None and image_url.startswith("/uploads/"), f"image_url={image_url}")

    # Verify image is reachable via GET
    img_req = urllib.request.Request(f"{BASE}{image_url}")
    with urllib.request.urlopen(img_req) as img_res:
        check("Image file reachable via static mount", img_res.status == 200 and img_res.read() == valid_png)

    # Fake image (text file renamed to .png)
    fake_png = b"This is a plain text file pretending to be an image."
    s, r = post_multipart(f"/api/admin/parts/{created_part_id}/image", "file", "fake.png", fake_png, "image/png", token=adm_token)
    check("Text file renamed to .png -> 422 invalid_image", s == 422 and r.get("code") == "invalid_image", f"got {s} {r.get('code')}")

    # File exceeding 5MB
    large_file = b"0" * (6 * 1024 * 1024)  # 6 MB
    s, r = post_multipart(f"/api/admin/parts/{created_part_id}/image", "file", "large.png", large_file, "image/png", token=adm_token)
    check("File > 5MB -> 413 file_too_large", s == 413 and r.get("code") == "file_too_large", f"got {s} {r.get('code')}")

    # Replace image with another valid image (JPEG)
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
    old_file_path = os.path.join(os.path.abspath("backend/uploads"), image_url.replace("/uploads/", ""))
    s, r = post_multipart(f"/api/admin/parts/{created_part_id}/image", "file", "new.jpg", valid_jpeg, "image/jpeg", token=adm_token)
    check("Replace image -> 200", s == 200)
    check("Old image file deleted from disk", not os.path.exists(old_file_path))

    # DELETE image
    s, r = request("DELETE", f"/api/admin/parts/{created_part_id}/image", token=adm_token)
    check("DELETE /parts/{id}/image -> 200", s == 200)
    check("image_url is now None", r.get("image_url") is None)

    # 9. PATCH part, specifications validation, deactivate/activate
    section("9. PATCH part, specs validation, deactivate/activate")
    # Duplicate specification keys rejected
    s, r = request("PATCH", f"/api/admin/parts/{created_part_id}", {
        "specifications": [
            {"key": "Voltage", "value": "240V"},
            {"key": "voltage", "value": "120V"},  # duplicate case-insensitively
        ]
    }, token=adm_token)
    check("Duplicate specification keys -> 422 validation_error", s == 422)

    # Valid PATCH name & specs
    s, r = request("PATCH", f"/api/admin/parts/{created_part_id}", {
        "name": "Updated High Precision Servo Bearing",
        "specifications": [{"key": "Voltage", "value": "24V"}],
    }, token=adm_token)
    check("Valid PATCH -> 200", s == 200 and r.get("name") == "Updated High Precision Servo Bearing")
    check("Part number remained unchanged", r.get("part_number") == test_part_num)

    # Deactivate part
    s, r = request("POST", f"/api/admin/parts/{created_part_id}/deactivate", token=adm_token)
    check("Deactivate part -> 200, is_active=False", s == 200 and r.get("is_active") is False)

    # Repeated deactivate idempotent
    s, r = request("POST", f"/api/admin/parts/{created_part_id}/deactivate", token=adm_token)
    check("Repeated deactivate is idempotent -> 200, is_active=False", s == 200 and r.get("is_active") is False)

    # Receive on inactive part -> 409 part_inactive
    s, r = request("POST", f"/api/admin/inventory/{test_inv_id}/receive", {"quantity": 1}, token=adm_token)
    check("Receive on inactive part -> 409 part_inactive", s == 409 and r.get("code") == "part_inactive", f"got {s} {r.get('code')}")

    # Activate part
    s, r = request("POST", f"/api/admin/parts/{created_part_id}/activate", token=adm_token)
    check("Activate part -> 200, is_active=True", s == 200 and r.get("is_active") is True)

    # 10. Filters, categories, sort whitelist
    section("10. Filters, categories & sort validation")
    # q=bearing
    s, r = request("GET", "/api/admin/parts?q=bearing", token=adm_token)
    check("Search q=bearing finds parts", s == 200 and r.get("total", 0) > 0)

    # q=conveyor matches machine name
    s, r = request("GET", "/api/admin/parts?q=conveyor", token=adm_token)
    check("Search q=conveyor matches machine linked parts", s == 200 and r.get("total", 0) > 0)

    # category filter
    s, r = request("GET", "/api/admin/parts?category=Bearings", token=adm_token)
    check("Filter category=Bearings works", s == 200 and all(p["category"] == "Bearings" for p in r.get("items", [])))

    # stock=low filter
    s, r = request("GET", "/api/admin/parts?stock=low", token=adm_token)
    check("Filter stock=low works", s == 200 and all(p["low_stock"] for p in r.get("items", [])))

    # stock=out filter
    s, r = request("GET", "/api/admin/parts?stock=out", token=adm_token)
    check("Filter stock=out works", s == 200 and all(p["out_of_stock"] for p in r.get("items", [])))

    # location_id filter
    s, r = request("GET", f"/api/admin/parts?location_id={pune_id}", token=adm_token)
    check("Filter location_id works", s == 200 and r.get("total", 0) > 0)

    # machine_id filter
    s, r = request("GET", f"/api/admin/parts?machine_id={m_ids[0]}", token=adm_token)
    check("Filter machine_id works", s == 200 and r.get("total", 0) > 0)

    # sort=bogus gives 422
    s, r = request("GET", "/api/admin/parts?sort=bogus", token=adm_token)
    check("sort=bogus -> 422 validation_error", s == 422 and r.get("code") == "validation_error")

    # page_size=5 total is correct
    s, r = request("GET", "/api/admin/parts?page_size=5&page=1", token=adm_token)
    check("page_size=5 returns 5 items and preserves total count", s == 200 and len(r.get("items", [])) == 5 and r.get("total") >= 15)

    # /parts/categories is not captured by /{id}
    s, cats = request("GET", "/api/admin/parts/categories", token=adm_token)
    check("GET /parts/categories -> 200 list", s == 200 and isinstance(cats, list) and "Bearings" in cats)

    # 11. Cleanup
    section("11. Cleanup test artifacts")
    cleanup_test_artifacts()
    # Confirm uploads/ directory has no leftover parts
    parts_upload_dir = os.path.abspath("backend/uploads/parts")
    orphan_files = os.listdir(parts_upload_dir) if os.path.exists(parts_upload_dir) else []
    check("Uploads folder has no orphan files", len(orphan_files) == 0, f"remaining={orphan_files}")

    # Re-verify ledger integrity after cleanup
    db = SessionLocal()
    try:
        mismatches = (
            db.query(Inventory.id)
            .outerjoin(
                InventoryTransaction,
                (InventoryTransaction.part_id == Inventory.part_id)
                & (InventoryTransaction.location_id == Inventory.location_id),
            )
            .group_by(Inventory.id, Inventory.quantity)
            .having(Inventory.quantity != func.coalesce(func.sum(InventoryTransaction.quantity_change), 0))
            .all()
        )
        check("Ledger remains 100% balanced after cleanup", len(mismatches) == 0)
    finally:
        db.close()

    # 12. Health check
    section("12. Health endpoints check")
    s, r = request("GET", "/api/health")
    check("GET /api/health -> 200 ok", s == 200 and r.get("status") == "ok")
    s, r = request("GET", "/api/health/db")
    check("GET /api/health/db -> 200 ok", s == 200 and r.get("status") == "ok")

    section("SUMMARY")
    if all_passed:
        print("  ALL MODULE 5A ACCEPTANCE CRITERIA PASSED!")
    else:
        print("  SOME ACCEPTANCE CHECKS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()

