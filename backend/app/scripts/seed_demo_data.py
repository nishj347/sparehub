"""Idempotent, production-safe demo data seed script for SpareHub.

Creates master catalogue data (locations, machines, spare parts, links, opening stock)
without modifying or deleting existing records. Does NOT seed users, passwords, or secrets.

Usage:
    python -m app.scripts.seed_demo_data [--dry-run] [--yes]
"""
import argparse
import sys
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.machine import Machine
from app.models.part_machine import PartMachine
from app.models.spare_part import SparePart
from app.models.user import User

# ─── DEMO DATA DEFINITIONS ───────────────────────────────────────────────────

DEMO_LOCATIONS = [
    {"code": "HWD", "name": "ITC Haridwar", "city": "Haridwar"},
    {"code": "BLR", "name": "ITC Bengaluru", "city": "Bengaluru"},
    {"code": "PNQ", "name": "ITC Pune", "city": "Pune"},
    {"code": "BOM", "name": "ITC Mumbai", "city": "Mumbai"},
]

DEMO_MACHINES = [
    {"code": "C-14", "name": "Conveyor Machine C-14", "loc_code": "HWD"},
    {"code": "P-07", "name": "Packaging Machine P-07", "loc_code": "HWD"},
    {"code": "M-03", "name": "Mixer M-03", "loc_code": "HWD"},
    {"code": "CT-11", "name": "Cutting Machine CT-11", "loc_code": "HWD"},
    {"code": "CP-02", "name": "Compressor CP-02", "loc_code": "HWD"},
    {"code": "CL-05", "name": "Cooling Pump CL-05", "loc_code": "HWD"},
    {"code": "R-09", "name": "Rolling Machine R-09", "loc_code": "HWD"},
    {"code": "D-04", "name": "Dryer D-04", "loc_code": "HWD"},
    {"code": "F-12", "name": "Filling Machine F-12", "loc_code": "HWD"},
    {"code": "L-08", "name": "Labelling Machine L-08", "loc_code": "HWD"},
]

DEMO_PARTS = [
    {
        "part_number": "BRG-6205",
        "name": "Bearing 6205-2RS",
        "category": "Bearing",
        "manufacturer": "SKF",
        "description": "Deep-groove ball bearing used in industrial conveyor systems",
        "specifications": {"Type": "Deep Groove", "Bore": "25mm", "Outer Diameter": "52mm", "Width": "15mm"},
        "machine_codes": ["C-14", "P-07"],
    },
    {
        "part_number": "BRG-6308",
        "name": "Bearing 6308-2Z",
        "category": "Bearing",
        "manufacturer": "FAG",
        "description": "Single-row deep groove ball bearing with metal shielding on both sides",
        "specifications": {"Type": "Deep Groove", "Bore": "40mm", "Outer Diameter": "90mm", "Width": "23mm"},
        "machine_codes": ["CP-02", "CL-05"],
    },
    {
        "part_number": "CPL-L100",
        "name": "Jaw Coupling L100",
        "category": "Coupling",
        "manufacturer": "Lovejoy",
        "description": "Flexible jaw coupling element for shaft vibration dampening and misalignment",
        "specifications": {"Coupling Size": "L100", "Torque Rating": "46 Nm", "Material": "Buna-N"},
        "machine_codes": ["C-14", "M-03"],
    },
    {
        "part_number": "BLT-A52",
        "name": "V-Belt A52",
        "category": "Belt",
        "manufacturer": "Gates",
        "description": "Industrial wrapped classical profile V-belt for power transmission",
        "specifications": {"Profile": "A Section", "Pitch Length": "52 in", "Top Width": "13mm"},
        "machine_codes": ["M-03", "CT-11"],
    },
    {
        "part_number": "BLT-B78",
        "name": "V-Belt B78",
        "category": "Belt",
        "manufacturer": "Fenner",
        "description": "Heavy-duty classical wrapped V-belt designed for drive systems",
        "specifications": {"Profile": "B Section", "Pitch Length": "78 in", "Top Width": "17mm"},
        "machine_codes": ["CP-02", "R-09"],
    },
    {
        "part_number": "MTR-1HP",
        "name": "Induction Motor 1 HP",
        "category": "Motor",
        "manufacturer": "Siemens",
        "description": "Three-phase high-efficiency induction motor for continuous line operation",
        "specifications": {"Power": "1 HP (0.75 kW)", "Voltage": "415V", "RPM": "1440 RPM", "Frame": "80M"},
        "machine_codes": ["C-14", "F-12"],
    },
    {
        "part_number": "SEL-MS35",
        "name": "Mechanical Seal 35 mm",
        "category": "Seal",
        "manufacturer": "John Crane",
        "description": "Single cartridge mechanical seal for industrial slurry and process pumps",
        "specifications": {"Shaft Diameter": "35mm", "Pressure Max": "16 bar", "Face Material": "Silicon Carbide"},
        "machine_codes": ["CL-05"],
    },
    {
        "part_number": "FLT-AF200",
        "name": "Air Filter Element",
        "category": "Filter",
        "manufacturer": "Donaldson",
        "description": "High-efficiency pleated cartridge air filter for intake air filtration",
        "specifications": {"Efficiency": "99.9%", "Flow Rate": "200 CFM", "Micron Rating": "5 micron"},
        "machine_codes": ["CP-02", "D-04"],
    },
    {
        "part_number": "SNS-PX18",
        "name": "Proximity Sensor M18",
        "category": "Sensor",
        "manufacturer": "Omron",
        "description": "Inductive proximity sensor with shielded cylindrical brass body",
        "specifications": {"Sensing Distance": "8mm", "Output": "PNP NO", "Voltage": "10-30V DC", "Thread": "M18"},
        "machine_codes": ["P-07", "F-12", "L-08"],
    },
    {
        "part_number": "GSK-FL100",
        "name": "Flange Gasket DN100",
        "category": "Gasket",
        "manufacturer": "Garlock",
        "description": "Non-asbestos compressed fiber sheet gasket for ASME B16.5 flanges",
        "specifications": {"Nominal Size": "DN100 (4 in)", "Rating": "Class 150", "Thickness": "3mm"},
        "machine_codes": ["CL-05", "M-03"],
    },
    {
        "part_number": "FUS-16A",
        "name": "HRC Fuse 16 A",
        "category": "Fuse",
        "manufacturer": "Schneider Electric",
        "description": "High rupturing capacity link fuse for circuit protection against overload",
        "specifications": {"Rated Current": "16A", "Voltage": "500V AC", "Breaking Capacity": "80kA", "Size": "Size 00"},
        "machine_codes": ["CT-11", "L-08"],
    },
    {
        "part_number": "CHN-RC08",
        "name": "Roller Chain 08B",
        "category": "Chain",
        "manufacturer": "Renold",
        "description": "Precision steel roller chain for power transmission and conveying drives",
        "specifications": {"Standard": "BS 08B-1", "Pitch": "12.7mm (0.5 in)", "Roller Width": "7.75mm"},
        "machine_codes": ["C-14", "R-09"],
    },
    {
        "part_number": "SPR-C14",
        "name": "Conveyor Drive Sprocket",
        "category": "Sprocket",
        "manufacturer": "Renold",
        "description": "Hardened steel drive sprocket with machined bore and keyway for 08B chain",
        "specifications": {"Teeth": "24T", "Chain Pitch": "08B (1/2 in)", "Bore": "25mm with Keyway"},
        "machine_codes": ["C-14"],
    },
    {
        "part_number": "SNS-PT100",
        "name": "Temperature Sensor PT100",
        "category": "Sensor",
        "manufacturer": "WIKA",
        "description": "Resistance temperature detector probe with stainless steel thermowell",
        "specifications": {"Element": "Pt100 Class A", "Range": "-50 to +400°C", "Probe Length": "150mm", "Thread": "1/2 NPT"},
        "machine_codes": ["D-04", "M-03"],
    },
]

# Inventory distribution plan:
# - All 14 parts at Haridwar (HWD)
# - 8 parts also at Bengaluru (BLR)
# - Low stock at Haridwar (3 parts at or below min_stock): CPL-L100 (3 <= 5), SEL-MS35 (1 <= 2), FLT-AF200 (2 <= 4)
# - Zero stock at Haridwar but stocked at Bengaluru: MTR-1HP (0 at HWD, 3 at BLR)
DEMO_INVENTORY = [
    # 1. BRG-6205: HWD (12), BLR (6)
    {"part_number": "BRG-6205", "loc_code": "HWD", "quantity": 12, "min_stock": 5, "store": "Mechanical Store", "rack": "R14", "bin": "B07"},
    {"part_number": "BRG-6205", "loc_code": "BLR", "quantity": 6, "min_stock": 4, "store": "Mechanical Store", "rack": "R03", "bin": "B02"},

    # 2. BRG-6308: HWD (8), BLR (4)
    {"part_number": "BRG-6308", "loc_code": "HWD", "quantity": 8, "min_stock": 3, "store": "Mechanical Store", "rack": "R14", "bin": "B08"},
    {"part_number": "BRG-6308", "loc_code": "BLR", "quantity": 4, "min_stock": 2, "store": "Mechanical Store", "rack": "R03", "bin": "B03"},

    # 3. CPL-L100: HWD (3, min 5 - LOW STOCK)
    {"part_number": "CPL-L100", "loc_code": "HWD", "quantity": 3, "min_stock": 5, "store": "Mechanical Store", "rack": "R08", "bin": "B03"},

    # 4. BLT-A52: HWD (20), BLR (10)
    {"part_number": "BLT-A52", "loc_code": "HWD", "quantity": 20, "min_stock": 6, "store": "Spares Cage", "rack": "R04", "bin": "B10"},
    {"part_number": "BLT-A52", "loc_code": "BLR", "quantity": 10, "min_stock": 4, "store": "Spares Cage", "rack": "R02", "bin": "B04"},

    # 5. BLT-B78: HWD (15)
    {"part_number": "BLT-B78", "loc_code": "HWD", "quantity": 15, "min_stock": 5, "store": "Spares Cage", "rack": "R04", "bin": "B11"},

    # 6. MTR-1HP: HWD (0 - OUT OF STOCK), BLR (3)
    {"part_number": "MTR-1HP", "loc_code": "HWD", "quantity": 0, "min_stock": 2, "store": "Electrical Store", "rack": "R12", "bin": "B01"},
    {"part_number": "MTR-1HP", "loc_code": "BLR", "quantity": 3, "min_stock": 2, "store": "Electrical Store", "rack": "R04", "bin": "B05"},

    # 7. SEL-MS35: HWD (1, min 2 - LOW STOCK)
    {"part_number": "SEL-MS35", "loc_code": "HWD", "quantity": 1, "min_stock": 2, "store": "Spares Cage", "rack": "R02", "bin": "B01"},

    # 8. FLT-AF200: HWD (2, min 4 - LOW STOCK)
    {"part_number": "FLT-AF200", "loc_code": "HWD", "quantity": 2, "min_stock": 4, "store": "Electrical Store", "rack": "R05", "bin": "B04"},

    # 9. SNS-PX18: HWD (25), BLR (12)
    {"part_number": "SNS-PX18", "loc_code": "HWD", "quantity": 25, "min_stock": 8, "store": "Electrical Store", "rack": "R06", "bin": "B02"},
    {"part_number": "SNS-PX18", "loc_code": "BLR", "quantity": 12, "min_stock": 5, "store": "Electrical Store", "rack": "R01", "bin": "B02"},

    # 10. GSK-FL100: HWD (30)
    {"part_number": "GSK-FL100", "loc_code": "HWD", "quantity": 30, "min_stock": 10, "store": "Mechanical Store", "rack": "R10", "bin": "B05"},

    # 11. FUS-16A: HWD (40), BLR (20)
    {"part_number": "FUS-16A", "loc_code": "HWD", "quantity": 40, "min_stock": 15, "store": "Electrical Store", "rack": "R01", "bin": "B09"},
    {"part_number": "FUS-16A", "loc_code": "BLR", "quantity": 20, "min_stock": 10, "store": "Electrical Store", "rack": "R01", "bin": "B01"},

    # 12. CHN-RC08: HWD (10), BLR (5)
    {"part_number": "CHN-RC08", "loc_code": "HWD", "quantity": 10, "min_stock": 4, "store": "Mechanical Store", "rack": "R15", "bin": "B02"},
    {"part_number": "CHN-RC08", "loc_code": "BLR", "quantity": 5, "min_stock": 3, "store": "Mechanical Store", "rack": "R05", "bin": "B02"},

    # 13. SPR-C14: HWD (6)
    {"part_number": "SPR-C14", "loc_code": "HWD", "quantity": 6, "min_stock": 3, "store": "Mechanical Store", "rack": "R15", "bin": "B03"},

    # 14. SNS-PT100: HWD (7), BLR (4)
    {"part_number": "SNS-PT100", "loc_code": "HWD", "quantity": 7, "min_stock": 3, "store": "Electrical Store", "rack": "R06", "bin": "B05"},
    {"part_number": "SNS-PT100", "loc_code": "BLR", "quantity": 4, "min_stock": 2, "store": "Electrical Store", "rack": "R02", "bin": "B01"},
]


def self_check_inventory(session: Session) -> Tuple[bool, List[str]]:
    """Validate that every inventory row's quantity equals SUM(quantity_change) and latest quantity_after."""
    items = session.scalars(select(Inventory)).all()
    mismatches: List[str] = []

    for item in items:
        txs = session.scalars(
            select(InventoryTransaction)
            .where(
                InventoryTransaction.part_id == item.part_id,
                InventoryTransaction.location_id == item.location_id,
            )
            .order_by(
                InventoryTransaction.created_at.asc(),
                InventoryTransaction.id.asc(),
            )
        ).all()

        if not txs:
            if item.quantity != 0:
                mismatches.append(
                    f"Inventory [ID: {item.id}, Part: {item.part_id}, Loc: {item.location_id}]: "
                    f"quantity={item.quantity} > 0 but no ledger transactions exist."
                )
            continue

        sum_change = sum(tx.quantity_change for tx in txs)
        if sum_change != item.quantity:
            mismatches.append(
                f"Inventory [ID: {item.id}, Part: {item.part_id}, Loc: {item.location_id}]: "
                f"SUM(quantity_change)={sum_change} != inventory.quantity={item.quantity}"
            )

        latest_tx = txs[-1]
        if latest_tx.quantity_after != item.quantity:
            mismatches.append(
                f"Inventory [ID: {item.id}, Part: {item.part_id}, Loc: {item.location_id}]: "
                f"latest quantity_after={latest_tx.quantity_after} != inventory.quantity={item.quantity}"
            )

    return (len(mismatches) == 0, mismatches)


def run_seed(session: Session, dry_run: bool = False) -> Dict[str, Any]:
    """Execute the idempotent seed operation within a single transaction."""
    stats = {
        "locations_created": 0,
        "locations_skipped": 0,
        "machines_created": 0,
        "machines_skipped": 0,
        "parts_created": 0,
        "parts_skipped": 0,
        "links_created": 0,
        "links_skipped": 0,
        "inventory_created": 0,
        "inventory_skipped": 0,
        "transactions_created": 0,
    }

    # ── 1. Find Admin Actor ──────────────────────────────────────────────────
    admin = session.scalar(
        select(User).where(
            func.lower(User.employee_id) == "adm001",
            User.role == UserRole.STORE_ADMIN,
            User.is_active == True,
        )
    )
    if not admin:
        admin = session.scalar(
            select(User).where(
                User.role == UserRole.STORE_ADMIN,
                User.is_active == True,
            ).order_by(User.id.asc())
        )

    if not admin:
        raise ValueError(
            "No active STORE_ADMIN user found to record opening stock transactions. "
            "Please create an admin user first (e.g. via python -m app.scripts.create_admin)."
        )

    # ── 2. Locations (Case-insensitive match) ─────────────────────────────────
    location_map: Dict[str, Location] = {}
    for l_data in DEMO_LOCATIONS:
        code_upper = l_data["code"].upper()
        existing = session.scalar(
            select(Location).where(func.lower(Location.code) == l_data["code"].lower())
        )
        if existing:
            stats["locations_skipped"] += 1
            location_map[code_upper] = existing
        else:
            new_loc = Location(
                code=code_upper,
                name=l_data["name"],
                city=l_data["city"],
                is_active=True,
            )
            session.add(new_loc)
            session.flush()
            stats["locations_created"] += 1
            location_map[code_upper] = new_loc

    # Special check: Haridwar can be under HWD or hwd
    hwd_loc = location_map.get("HWD")
    if not hwd_loc:
        raise ValueError("Could not resolve or create Haridwar location.")

    # ── 3. Machines ──────────────────────────────────────────────────────────
    machine_map: Dict[str, Machine] = {}
    for m_data in DEMO_MACHINES:
        code_upper = m_data["code"].upper()
        existing = session.scalar(
            select(Machine).where(func.lower(Machine.code) == m_data["code"].lower())
        )
        if existing:
            stats["machines_skipped"] += 1
            machine_map[code_upper] = existing
        else:
            loc = location_map.get(m_data["loc_code"].upper(), hwd_loc)
            new_m = Machine(
                code=m_data["code"],
                name=m_data["name"],
                location_id=loc.id,
                is_active=True,
            )
            session.add(new_m)
            session.flush()
            stats["machines_created"] += 1
            machine_map[code_upper] = new_m

    # ── 4. Spare Parts ───────────────────────────────────────────────────────
    part_map: Dict[str, SparePart] = {}
    for p_data in DEMO_PARTS:
        p_num_upper = p_data["part_number"].upper()
        existing = session.scalar(
            select(SparePart).where(func.lower(SparePart.part_number) == p_data["part_number"].lower())
        )
        if existing:
            stats["parts_skipped"] += 1
            part_map[p_num_upper] = existing
        else:
            new_part = SparePart(
                part_number=p_data["part_number"],
                name=p_data["name"],
                category=p_data["category"],
                manufacturer=p_data.get("manufacturer"),
                description=p_data.get("description"),
                specifications=p_data.get("specifications"),
                image_path=None,
                is_active=True,
            )
            session.add(new_part)
            session.flush()
            stats["parts_created"] += 1
            part_map[p_num_upper] = new_part

        # Part-Machine Links
        target_part = part_map[p_num_upper]
        for m_code in p_data.get("machine_codes", []):
            mach = machine_map.get(m_code.upper())
            if mach:
                link_exists = session.scalar(
                    select(PartMachine.part_id).where(
                        PartMachine.part_id == target_part.id,
                        PartMachine.machine_id == mach.id,
                    )
                )
                if link_exists:
                    stats["links_skipped"] += 1
                else:
                    new_link = PartMachine(part_id=target_part.id, machine_id=mach.id)
                    session.add(new_link)
                    session.flush()
                    stats["links_created"] += 1

    # ── 5. Inventory & Opening Ledger Transactions ───────────────────────────
    for inv_data in DEMO_INVENTORY:
        part = part_map.get(inv_data["part_number"].upper())
        loc = location_map.get(inv_data["loc_code"].upper())
        if not part or not loc:
            continue

        existing_inv = session.scalar(
            select(Inventory).where(
                Inventory.part_id == part.id,
                Inventory.location_id == loc.id,
            )
        )

        if existing_inv:
            stats["inventory_skipped"] += 1
        else:
            new_inv = Inventory(
                part_id=part.id,
                location_id=loc.id,
                quantity=inv_data["quantity"],
                min_stock_level=inv_data["min_stock"],
                store_name=inv_data.get("store"),
                rack=inv_data.get("rack"),
                bin=inv_data.get("bin"),
            )
            session.add(new_inv)
            session.flush()
            stats["inventory_created"] += 1

            # Only create an opening transaction if quantity > 0
            if inv_data["quantity"] > 0:
                tx = InventoryTransaction(
                    part_id=part.id,
                    location_id=loc.id,
                    user_id=admin.id,
                    transaction_type=TransactionType.RECEIVED,
                    quantity_change=inv_data["quantity"],
                    quantity_after=inv_data["quantity"],
                    notes="Opening stock (demo data)",
                )
                session.add(tx)
                session.flush()
                stats["transactions_created"] += 1

    # ── 6. Self-check Invariant ──────────────────────────────────────────────
    valid, errors = self_check_inventory(session)
    if not valid:
        raise ValueError("Inventory ledger consistency check FAILED:\n" + "\n".join(errors))

    if dry_run:
        session.rollback()
    else:
        session.commit()

    return stats


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Idempotent demo-data seed for SpareHub."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the seed without committing any changes to the database.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Bypass interactive confirmation prompt.",
    )
    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)
    settings = get_settings()

    db_url = settings.DATABASE_URL
    if not db_url or not db_url.strip():
        print("[ERROR] DATABASE_URL environment variable is missing or empty.", file=sys.stderr)
        sys.exit(1)

    url_info = urlparse(db_url)
    db_host = url_info.hostname or "localhost"
    db_name = url_info.path.lstrip("/") or "default"

    print("=" * 65)
    print("           SPAREHUB IDEMPOTENT DEMO DATA SEED")
    print("=" * 65)
    print(f"Target Database Host : {db_host}")
    print(f"Target Database Name : {db_name}")
    print(f"Execution Mode       : {'DRY RUN (no changes saved)' if parsed.dry_run else 'LIVE WRITE'}")
    print("=" * 65)

    if not parsed.dry_run and not parsed.yes:
        try:
            confirm = input("Are you sure you want to seed demo data into this database? [y/N]: ")
            if confirm.strip().lower() not in ("y", "yes"):
                print("Seeding canceled by user.")
                sys.exit(0)
        except EOFError:
            print("[ERROR] Non-interactive environment detected. Pass --yes to confirm execution.", file=sys.stderr)
            sys.exit(1)

    session = SessionLocal()
    try:
        stats = run_seed(session, dry_run=parsed.dry_run)
        print("\n" + "=" * 65)
        print("SEEDING SUMMARY")
        print("=" * 65)
        print(f"Locations       : {stats['locations_created']} created, {stats['locations_skipped']} skipped (already present)")
        print(f"Machines        : {stats['machines_created']} created, {stats['machines_skipped']} skipped (already present)")
        print(f"Spare Parts     : {stats['parts_created']} created, {stats['parts_skipped']} skipped (already present)")
        print(f"Part-Machine Links: {stats['links_created']} created, {stats['links_skipped']} skipped (already present)")
        print(f"Inventory Rows  : {stats['inventory_created']} created, {stats['inventory_skipped']} skipped (already present)")
        print(f"Opening Tx Ledger: {stats['transactions_created']} created")
        print("=" * 65)
        print("[OK] Self-check PASSED: All inventory rows match ledger transaction history exactly.")
        if parsed.dry_run:
            print("\n[DRY RUN COMPLETE] No records were committed to the database.")
        else:
            print("\n[SUCCESS] Seed committed successfully in a single atomic transaction.")
    except Exception as exc:
        session.rollback()
        print(f"\n[ERROR] Seeding failed and changes were rolled back:\n{exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
