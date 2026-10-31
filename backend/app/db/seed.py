"""Development database seed script for Spare Parts Management & Discovery System.

Usage:
    python -m app.db.seed [--reset]
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import TransactionType, UserRole
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.location import Location
from app.models.machine import Machine
from app.models.notification import Notification
from app.models.part_machine import PartMachine
from app.models.spare_part import SparePart
from app.models.user import User


def check_environment() -> str:
    """Validate that seeding is allowed in current environment and return default password."""
    settings = get_settings()
    if settings.is_production:
        sys.stderr.write(
            "\n[FATAL] Seeding is strictly forbidden in production (APP_ENV=production).\n"
        )
        sys.exit(1)

    password = settings.SEED_DEFAULT_PASSWORD
    if not password or not password.strip():
        sys.stderr.write(
            "\n[FATAL] SEED_DEFAULT_PASSWORD environment variable is missing or empty. "
            "Please configure SEED_DEFAULT_PASSWORD in backend/.env before running the seed script.\n"
        )
        sys.exit(1)

    return password.strip()


def reset_database(session: Session) -> None:
    """Delete all rows in reverse foreign-key dependency order."""
    print("Resetting database (deleting all existing records)...")
    session.execute(delete(Notification))
    session.execute(delete(PartMachine))
    session.execute(delete(InventoryTransaction))
    session.execute(delete(Inventory))
    session.execute(delete(User))
    session.execute(delete(Machine))
    session.execute(delete(SparePart))
    session.execute(delete(Location))
    session.flush()
    print("Database reset completed successfully.")


def seed_locations(session: Session) -> Dict[str, Location]:
    """Seed the 4 standard ITC locations."""
    locations_data = [
        {"name": "ITC Bengaluru", "code": "BLR", "city": "Bengaluru"},
        {"name": "ITC Delhi", "code": "DEL", "city": "Delhi"},
        {"name": "ITC Pune", "code": "PNQ", "city": "Pune"},
        {"name": "ITC Mumbai", "code": "BOM", "city": "Mumbai"},
    ]

    location_map: Dict[str, Location] = {}
    created_count = 0
    existing_count = 0

    for data in locations_data:
        existing = session.scalars(
            select(Location).where(Location.code == data["code"])
        ).first()
        if existing:
            location_map[data["code"]] = existing
            existing_count += 1
        else:
            loc = Location(
                name=data["name"],
                code=data["code"],
                city=data["city"],
                is_active=True,
            )
            session.add(loc)
            session.flush()
            location_map[data["code"]] = loc
            created_count += 1

    print(f"Locations: {created_count} created, {existing_count} already existed.")
    return location_map


def seed_users(
    session: Session,
    location_map: Dict[str, Location],
    default_password: str,
) -> Dict[str, User]:
    """Seed 1 Store Admin and 4 Employees."""
    hashed_pwd = hash_password(default_password)

    users_data = [
        {
            "employee_id": "ITCADM001",
            "name": "Rajesh Sharma",
            "email": "rajesh.sharma@example-itc.test",
            "role": UserRole.STORE_ADMIN,
            "location_code": "BLR",
        },
        {
            "employee_id": "ITC10452",
            "name": "Priya Patel",
            "email": "priya.patel@example-itc.test",
            "role": UserRole.EMPLOYEE,
            "location_code": "BLR",
        },
        {
            "employee_id": "ITC10221",
            "name": "Amit Kumar",
            "email": "amit.kumar@example-itc.test",
            "role": UserRole.EMPLOYEE,
            "location_code": "BLR",
        },
        {
            "employee_id": "ITC10388",
            "name": "Sunita Rao",
            "email": "sunita.rao@example-itc.test",
            "role": UserRole.EMPLOYEE,
            "location_code": "PNQ",
        },
        {
            "employee_id": "ITC10517",
            "name": "Vikram Singh",
            "email": "vikram.singh@example-itc.test",
            "role": UserRole.EMPLOYEE,
            "location_code": "DEL",
        },
    ]

    user_map: Dict[str, User] = {}
    created_count = 0
    existing_count = 0

    for u in users_data:
        existing = session.scalars(
            select(User).where(User.employee_id == u["employee_id"])
        ).first()
        if existing:
            user_map[u["employee_id"]] = existing
            existing_count += 1
        else:
            new_user = User(
                employee_id=u["employee_id"],
                name=u["name"],
                email=u["email"].lower(),
                password_hash=hashed_pwd,
                role=u["role"],
                location_id=location_map[u["location_code"]].id,
                is_active=True,
            )
            session.add(new_user)
            session.flush()
            user_map[u["employee_id"]] = new_user
            created_count += 1

    print(f"Users: {created_count} created, {existing_count} already existed.")
    return user_map


def seed_machines(
    session: Session, location_map: Dict[str, Location]
) -> Dict[str, Machine]:
    """Seed 8 industrial machines across locations."""
    machines_data = [
        {"name": "Conveyor Machine C-14", "code": "C-14", "location_code": "BLR"},
        {"name": "Packaging Machine P-07", "code": "P-07", "location_code": "BLR"},
        {"name": "Mixer M-03", "code": "M-03", "location_code": "PNQ"},
        {"name": "Cutting Machine CT-11", "code": "CT-11", "location_code": "DEL"},
        {"name": "Compressor CP-02", "code": "CP-02", "location_code": "BOM"},
        {"name": "Cooling Pump CL-05", "code": "CL-05", "location_code": "BLR"},
        {"name": "Rolling Machine R-09", "code": "R-09", "location_code": "PNQ"},
        {"name": "Dryer D-04", "code": "D-04", "location_code": "DEL"},
    ]

    machine_map: Dict[str, Machine] = {}
    created_count = 0
    existing_count = 0

    for m in machines_data:
        existing = session.scalars(
            select(Machine).where(Machine.code == m["code"])
        ).first()
        if existing:
            machine_map[m["code"]] = existing
            existing_count += 1
        else:
            loc = location_map.get(m["location_code"])
            new_machine = Machine(
                name=m["name"],
                code=m["code"],
                location_id=loc.id if loc else None,
            )
            session.add(new_machine)
            session.flush()
            machine_map[m["code"]] = new_machine
            created_count += 1

    print(f"Machines: {created_count} created, {existing_count} already existed.")
    return machine_map


def seed_spare_parts_and_links(
    session: Session, machine_map: Dict[str, Machine]
) -> Dict[str, SparePart]:
    """Seed 15 spare parts and part_machines links."""
    parts_data = [
        {
            "part_number": "BRG-6205",
            "name": "Bearing 6205-2RS",
            "category": "Bearing",
            "manufacturer": "SKF",
            "description": "Deep-groove ball bearing used in industrial conveyor systems",
            "specifications": {
                "model": "6205-2RS",
                "category": "Bearing",
                "bore_diameter": "25mm",
                "outer_diameter": "52mm",
                "width": "15mm",
                "seal_type": "Rubber Seal (2RS)",
            },
            "machines": ["C-14", "P-07"],
        },
        {
            "part_number": "BRG-6309",
            "name": "Deep Groove Ball Bearing 6309-2Z",
            "category": "Bearing",
            "manufacturer": "FAG",
            "description": "Single row deep groove ball bearing with steel shields for heavy motor drives",
            "specifications": {
                "model": "6309-2Z",
                "bore_diameter": "45mm",
                "outer_diameter": "100mm",
                "width": "25mm",
                "cage_material": "Pressed Steel",
            },
            "machines": ["CP-02", "M-03"],
        },
        {
            "part_number": "CPL-FLEX-080",
            "name": "Flexible Jaw Coupling 80mm",
            "category": "Coupling",
            "manufacturer": "Lovejoy",
            "description": "Elastomeric flexible jaw coupling for dampening vibration and shaft misalignment",
            "specifications": {
                "hub_bore": "28mm",
                "max_torque_nm": 160,
                "spider_material": "Polyurethane",
                "outer_diameter": "80mm",
            },
            "machines": ["C-14", "CL-05"],
        },
        {
            "part_number": "BLT-V-B68",
            "name": "Classical V-Belt B68",
            "category": "Belt",
            "manufacturer": "Gates",
            "description": "Heavy-duty wrapped V-belt for industrial drive pulleys",
            "specifications": {
                "profile": "B",
                "inside_length": "68 inch",
                "pitch_length": "70.8 inch",
                "top_width": "17mm",
            },
            "machines": ["P-07", "R-09"],
        },
        {
            "part_number": "BLT-TIM-T10",
            "name": "Timing Belt T10-1200-25",
            "category": "Belt",
            "manufacturer": "ContiTech",
            "description": "Polyurethane metric timing belt with steel tension cords for synchronous indexing",
            "specifications": {
                "pitch": "10mm",
                "length": "1200mm",
                "width": "25mm",
                "teeth": 120,
            },
            "machines": ["P-07", "CT-11"],
        },
        {
            "part_number": "MTR-IND-3KW",
            "name": "Three-Phase Induction Motor 3kW",
            "category": "Motor",
            "manufacturer": "Siemens",
            "description": "IE3 premium efficiency 4-pole cast iron electric motor 415V",
            "specifications": {
                "power_kw": 3.0,
                "rpm": 1450,
                "voltage": "415V",
                "frame": "100L",
                "mounting": "Foot/B3",
            },
            "machines": ["C-14", "M-03"],
        },
        {
            "part_number": "MTR-SER-750W",
            "name": "AC Servo Motor 750W",
            "category": "Motor",
            "manufacturer": "Schneider Electric",
            "description": "Brushless synchronous AC servo motor with absolute multi-turn optical encoder",
            "specifications": {
                "power_w": 750,
                "nominal_speed_rpm": 3000,
                "rated_torque_nm": 2.4,
                "ip_rating": "IP65",
            },
            "machines": ["P-07", "CT-11"],
        },
        {
            "part_number": "SEL-OIL-4570",
            "name": "Radial Oil Seal 45x70x10",
            "category": "Seal",
            "manufacturer": "Freudenberg",
            "description": "Rotary shaft seal with spring-energized sealing lip for gearbox output shafts",
            "specifications": {
                "inner_diameter": "45mm",
                "outer_diameter": "70mm",
                "width": "10mm",
                "material": "NBR 70",
            },
            "machines": ["CP-02", "CL-05"],
        },
        {
            "part_number": "SEL-MEC-32",
            "name": "Cartridge Mechanical Seal 32mm",
            "category": "Seal",
            "manufacturer": "Burgmann",
            "description": "Single balanced cartridge mechanical seal for industrial cooling water pumps",
            "specifications": {
                "shaft_size": "32mm",
                "face_materials": "SiC/SiC",
                "elastomer": "FKM",
                "max_pressure_bar": 16,
            },
            "machines": ["CL-05"],
        },
        {
            "part_number": "FLT-AIR-02",
            "name": "Compressor Air Intake Filter",
            "category": "Filter",
            "manufacturer": "Donaldson",
            "description": "Heavy-duty cellulose air filter element for reciprocating and rotary compressors",
            "specifications": {
                "efficiency": "99.9% @ 5 micron",
                "flow_rate_cfm": 250,
                "height": "220mm",
            },
            "machines": ["CP-02"],
        },
        {
            "part_number": "FLT-HYD-10U",
            "name": "Hydraulic Return Filter 10 Micron",
            "category": "Filter",
            "manufacturer": "Hydac",
            "description": "Micro-glass hydraulic fluid filter cartridge for high-pressure hydraulic circuits",
            "specifications": {
                "micron_rating": 10,
                "collapse_pressure_bar": 210,
                "length": "180mm",
            },
            "machines": ["CT-11", "R-09"],
        },
        {
            "part_number": "SNS-PROX-M18",
            "name": "Inductive Proximity Sensor M18",
            "category": "Sensor",
            "manufacturer": "Omron",
            "description": "Flush mounted cylindrical inductive sensor with PNP normally open output",
            "specifications": {
                "sensing_distance": "8mm",
                "output_type": "PNP NO",
                "supply_voltage": "10-30V DC",
                "ip_rating": "IP67",
            },
            "machines": ["C-14", "P-07", "CT-11"],
        },
        {
            "part_number": "SNS-TEMP-PT100",
            "name": "RTD Pt100 Temperature Probe",
            "category": "Sensor",
            "manufacturer": "Endress+Hauser",
            "description": "Class A 3-wire mineral insulated Pt100 temperature sensor with 1/2-inch BSP connector",
            "specifications": {
                "sensor_type": "Pt100",
                "sheath_diameter": "6mm",
                "immersion_length": "150mm",
                "temperature_range": "-50C to +400C",
            },
            "machines": ["M-03", "D-04"],
        },
        {
            "part_number": "GSK-FLG-DN50",
            "name": "Spiral Wound Flange Gasket DN50",
            "category": "Gasket",
            "manufacturer": "Klinger",
            "description": "SS316L graphite filled spiral wound gasket with outer centering ring PN40",
            "specifications": {
                "nominal_size": "DN50",
                "pressure_class": "PN40",
                "winding_material": "SS316L",
                "filler": "Flexible Graphite",
            },
            "machines": ["CL-05", "D-04"],
        },
        {
            "part_number": "FUS-HRC-63A",
            "name": "NH Industrial HRC Fuse Link 63A",
            "category": "Fuse",
            "manufacturer": "Bussmann",
            "description": "NH00 knife-blade gG general industrial ceramic body fuse link 500V 63A",
            "specifications": {
                "size": "NH00",
                "current_rating": "63A",
                "voltage_ac": "500V",
                "breaking_capacity_ka": 120,
            },
            "machines": ["C-14", "M-03", "R-09"],
        },
    ]

    part_map: Dict[str, SparePart] = {}
    parts_created = 0
    parts_existing = 0
    links_created = 0
    links_existing = 0

    for p in parts_data:
        existing = session.scalars(
            select(SparePart).where(SparePart.part_number == p["part_number"])
        ).first()
        if existing:
            part_map[p["part_number"]] = existing
            part_obj = existing
            parts_existing += 1
        else:
            new_part = SparePart(
                part_number=p["part_number"],
                name=p["name"],
                category=p["category"],
                manufacturer=p["manufacturer"],
                description=p["description"],
                specifications=p["specifications"],
                image_path=None,
                is_active=True,
            )
            session.add(new_part)
            session.flush()
            part_map[p["part_number"]] = new_part
            part_obj = new_part
            parts_created += 1

        # Link to machines
        for m_code in p["machines"]:
            mach = machine_map.get(m_code)
            if mach:
                link_exists = session.scalars(
                    select(PartMachine).where(
                        PartMachine.part_id == part_obj.id,
                        PartMachine.machine_id == mach.id,
                    )
                ).first()
                if not link_exists:
                    session.add(PartMachine(part_id=part_obj.id, machine_id=mach.id))
                    links_created += 1
                else:
                    links_existing += 1

    session.flush()
    print(f"Spare Parts: {parts_created} created, {parts_existing} already existed.")
    print(f"Part-Machine Links: {links_created} created, {links_existing} already existed.")
    return part_map


def seed_inventory_and_transactions(
    session: Session,
    location_map: Dict[str, Location],
    part_map: Dict[str, SparePart],
    user_map: Dict[str, User],
) -> None:
    """Seed inventory items and ledger transactions."""
    admin = user_map["ITCADM001"]
    emp_priya = user_map["ITC10452"]
    emp_amit = user_map["ITC10221"]
    emp_vikram = user_map["ITC10517"]
    emp_sunita = user_map["ITC10388"]

    now = datetime.now(timezone.utc)

    # Detailed inventory distribution plan:
    # 1. BRG-6205: BLR (12), PNQ (6), BOM (3), DEL (0)
    #    BLR has history: +20 (admin), -5 (ITC10452), -3 (ITC10221) -> 12
    #    PNQ: +6
    #    BOM: +3 (<= min 5)
    #    DEL: +4, -4 -> 0
    # 2. MTR-SER-750W: BLR (2), PNQ (0), DEL (0) -> 0 stock everywhere except BLR!
    # 3. SEL-MEC-32: BLR (1, min 2) -> at/below min stock
    # 4. FLT-AIR-02: BOM (2, min 2) -> at/below min stock
    # 5. SNS-TEMP-PT100: DEL (1, min 3) -> at/below min stock
    inventory_plan = [
        # BRG-6205
        {
            "part_code": "BRG-6205",
            "loc_code": "BLR",
            "quantity": 12,
            "min_stock_level": 10,
            "store_name": "Mechanical Store",
            "rack": "R14",
            "bin": "B07",
            "history": [
                {
                    "type": TransactionType.RECEIVED,
                    "change": 20,
                    "after": 20,
                    "user": admin,
                    "delta_days": 10,
                    "notes": "Initial stock receipt from SKF distributor",
                },
                {
                    "type": TransactionType.ISSUED,
                    "change": -5,
                    "after": 15,
                    "user": emp_priya,
                    "delta_days": 5,
                    "notes": "Issued for Conveyor C-14 scheduled roller overhaul",
                },
                {
                    "type": TransactionType.ISSUED,
                    "change": -3,
                    "after": 12,
                    "user": emp_amit,
                    "delta_days": 2,
                    "notes": "Issued for Packaging P-07 drive replacement",
                },
            ],
        },
        {
            "part_code": "BRG-6205",
            "loc_code": "PNQ",
            "quantity": 6,
            "min_stock_level": 5,
            "store_name": "Central Spares",
            "rack": "R03",
            "bin": "B12",
            "history": [
                {
                    "type": TransactionType.RECEIVED,
                    "change": 6,
                    "after": 6,
                    "user": admin,
                    "delta_days": 8,
                    "notes": "Stock transfer from central warehouse",
                }
            ],
        },
        {
            "part_code": "BRG-6205",
            "loc_code": "BOM",
            "quantity": 3,
            "min_stock_level": 5,
            "store_name": "Maintenance Hub",
            "rack": "R08",
            "bin": "B01",
            "history": [
                {
                    "type": TransactionType.RECEIVED,
                    "change": 3,
                    "after": 3,
                    "user": admin,
                    "delta_days": 7,
                    "notes": "Emergency stock replenishment",
                }
            ],
        },
        {
            "part_code": "BRG-6205",
            "loc_code": "DEL",
            "quantity": 0,
            "min_stock_level": 4,
            "store_name": "Delhi Spares Room",
            "rack": "R01",
            "bin": "B02",
            "history": [
                {
                    "type": TransactionType.RECEIVED,
                    "change": 4,
                    "after": 4,
                    "user": admin,
                    "delta_days": 12,
                    "notes": "Opening stock receipt",
                },
                {
                    "type": TransactionType.ISSUED,
                    "change": -4,
                    "after": 0,
                    "user": emp_vikram,
                    "delta_days": 3,
                    "notes": "Emergency replacement on cutting line; stock depleted",
                },
            ],
        },
        # BRG-6309
        {
            "part_code": "BRG-6309",
            "loc_code": "BOM",
            "quantity": 8,
            "min_stock_level": 4,
            "store_name": "Maintenance Hub",
            "rack": "R08",
            "bin": "B03",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 8, "after": 8, "user": admin, "delta_days": 14, "notes": "FAG shipment"}
            ],
        },
        {
            "part_code": "BRG-6309",
            "loc_code": "PNQ",
            "quantity": 4,
            "min_stock_level": 3,
            "store_name": "Central Spares",
            "rack": "R03",
            "bin": "B14",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 4, "after": 4, "user": admin, "delta_days": 14, "notes": "Initial receipt"}
            ],
        },
        # CPL-FLEX-080
        {
            "part_code": "CPL-FLEX-080",
            "loc_code": "BLR",
            "quantity": 5,
            "min_stock_level": 3,
            "store_name": "Mechanical Store",
            "rack": "R12",
            "bin": "B04",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 5, "after": 5, "user": admin, "delta_days": 11, "notes": "Initial receipt"}
            ],
        },
        {
            "part_code": "CPL-FLEX-080",
            "loc_code": "DEL",
            "quantity": 2,
            "min_stock_level": 2,
            "store_name": "Delhi Spares Room",
            "rack": "R02",
            "bin": "B01",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 2, "after": 2, "user": admin, "delta_days": 11, "notes": "Initial receipt"}
            ],
        },
        # BLT-V-B68
        {
            "part_code": "BLT-V-B68",
            "loc_code": "BLR",
            "quantity": 15,
            "min_stock_level": 5,
            "store_name": "Mechanical Store",
            "rack": "R05",
            "bin": "B10",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 15, "after": 15, "user": admin, "delta_days": 15, "notes": "Gates bulk batch"}
            ],
        },
        {
            "part_code": "BLT-V-B68",
            "loc_code": "PNQ",
            "quantity": 7,
            "min_stock_level": 4,
            "store_name": "Central Spares",
            "rack": "R04",
            "bin": "B05",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 7, "after": 7, "user": admin, "delta_days": 15, "notes": "Initial receipt"}
            ],
        },
        # BLT-TIM-T10
        {
            "part_code": "BLT-TIM-T10",
            "loc_code": "BLR",
            "quantity": 6,
            "min_stock_level": 3,
            "store_name": "Mechanical Store",
            "rack": "R05",
            "bin": "B12",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 6, "after": 6, "user": admin, "delta_days": 10, "notes": "Initial receipt"}
            ],
        },
        {
            "part_code": "BLT-TIM-T10",
            "loc_code": "DEL",
            "quantity": 3,
            "min_stock_level": 2,
            "store_name": "Delhi Spares Room",
            "rack": "R02",
            "bin": "B08",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 3, "after": 3, "user": admin, "delta_days": 10, "notes": "Initial receipt"}
            ],
        },
        # MTR-IND-3KW
        {
            "part_code": "MTR-IND-3KW",
            "loc_code": "BLR",
            "quantity": 2,
            "min_stock_level": 1,
            "store_name": "Electrical Store",
            "rack": "E01",
            "bin": "Floor-01",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 2, "after": 2, "user": admin, "delta_days": 20, "notes": "Siemens delivery"}
            ],
        },
        {
            "part_code": "MTR-IND-3KW",
            "loc_code": "PNQ",
            "quantity": 1,
            "min_stock_level": 1,
            "store_name": "Central Spares",
            "rack": "E02",
            "bin": "Floor-02",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 1, "after": 1, "user": admin, "delta_days": 20, "notes": "Siemens delivery"}
            ],
        },
        # MTR-SER-750W (0 stock everywhere except BLR!)
        {
            "part_code": "MTR-SER-750W",
            "loc_code": "BLR",
            "quantity": 2,
            "min_stock_level": 1,
            "store_name": "Electrical Store",
            "rack": "E03",
            "bin": "B01",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 2, "after": 2, "user": admin, "delta_days": 16, "notes": "Schneider shipment"}
            ],
        },
        {
            "part_code": "MTR-SER-750W",
            "loc_code": "PNQ",
            "quantity": 0,
            "min_stock_level": 1,
            "store_name": "Central Spares",
            "rack": "E01",
            "bin": "B02",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 1, "after": 1, "user": admin, "delta_days": 14, "notes": "Initial unit"},
                {"type": TransactionType.ISSUED, "change": -1, "after": 0, "user": emp_sunita, "delta_days": 4, "notes": "Issued to Mixer M-03; out of stock"},
            ],
        },
        {
            "part_code": "MTR-SER-750W",
            "loc_code": "DEL",
            "quantity": 0,
            "min_stock_level": 1,
            "store_name": "Delhi Spares Room",
            "rack": "E01",
            "bin": "B01",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 1, "after": 1, "user": admin, "delta_days": 12, "notes": "Initial unit"},
                {"type": TransactionType.ISSUED, "change": -1, "after": 0, "user": emp_vikram, "delta_days": 2, "notes": "Issued to Cutting CT-11; out of stock"},
            ],
        },
        # SEL-OIL-4570
        {
            "part_code": "SEL-OIL-4570",
            "loc_code": "BOM",
            "quantity": 10,
            "min_stock_level": 5,
            "store_name": "Maintenance Hub",
            "rack": "R07",
            "bin": "B11",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 10, "after": 10, "user": admin, "delta_days": 9, "notes": "Initial receipt"}
            ],
        },
        {
            "part_code": "SEL-OIL-4570",
            "loc_code": "BLR",
            "quantity": 8,
            "min_stock_level": 4,
            "store_name": "Mechanical Store",
            "rack": "R09",
            "bin": "B02",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 8, "after": 8, "user": admin, "delta_days": 9, "notes": "Initial receipt"}
            ],
        },
        # SEL-MEC-32 (at/below min stock in BLR)
        {
            "part_code": "SEL-MEC-32",
            "loc_code": "BLR",
            "quantity": 1,
            "min_stock_level": 2,
            "store_name": "Mechanical Store",
            "rack": "R09",
            "bin": "B05",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 1, "after": 1, "user": admin, "delta_days": 15, "notes": "Single spare unit"}
            ],
        },
        {
            "part_code": "SEL-MEC-32",
            "loc_code": "BOM",
            "quantity": 3,
            "min_stock_level": 2,
            "store_name": "Maintenance Hub",
            "rack": "R07",
            "bin": "B12",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 3, "after": 3, "user": admin, "delta_days": 15, "notes": "Initial receipt"}
            ],
        },
        # FLT-AIR-02 (at/below min stock in BOM)
        {
            "part_code": "FLT-AIR-02",
            "loc_code": "BOM",
            "quantity": 2,
            "min_stock_level": 2,
            "store_name": "Maintenance Hub",
            "rack": "R02",
            "bin": "B04",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 2, "after": 2, "user": admin, "delta_days": 13, "notes": "Intake filter pack"}
            ],
        },
        {
            "part_code": "FLT-AIR-02",
            "loc_code": "PNQ",
            "quantity": 5,
            "min_stock_level": 3,
            "store_name": "Central Spares",
            "rack": "R06",
            "bin": "B03",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 5, "after": 5, "user": admin, "delta_days": 13, "notes": "Initial receipt"}
            ],
        },
        # FLT-HYD-10U
        {
            "part_code": "FLT-HYD-10U",
            "loc_code": "DEL",
            "quantity": 6,
            "min_stock_level": 3,
            "store_name": "Delhi Spares Room",
            "rack": "R03",
            "bin": "B07",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 6, "after": 6, "user": admin, "delta_days": 18, "notes": "Hydac batch"}
            ],
        },
        {
            "part_code": "FLT-HYD-10U",
            "loc_code": "PNQ",
            "quantity": 4,
            "min_stock_level": 2,
            "store_name": "Central Spares",
            "rack": "R06",
            "bin": "B08",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 4, "after": 4, "user": admin, "delta_days": 18, "notes": "Hydac batch"}
            ],
        },
        # SNS-PROX-M18
        {
            "part_code": "SNS-PROX-M18",
            "loc_code": "BLR",
            "quantity": 10,
            "min_stock_level": 4,
            "store_name": "Electrical Store",
            "rack": "E04",
            "bin": "B02",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 10, "after": 10, "user": admin, "delta_days": 11, "notes": "Omron shipment"}
            ],
        },
        {
            "part_code": "SNS-PROX-M18",
            "loc_code": "DEL",
            "quantity": 5,
            "min_stock_level": 3,
            "store_name": "Delhi Spares Room",
            "rack": "E02",
            "bin": "B03",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 5, "after": 5, "user": admin, "delta_days": 11, "notes": "Initial receipt"}
            ],
        },
        {
            "part_code": "SNS-PROX-M18",
            "loc_code": "PNQ",
            "quantity": 7,
            "min_stock_level": 3,
            "store_name": "Central Spares",
            "rack": "E03",
            "bin": "B05",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 7, "after": 7, "user": admin, "delta_days": 11, "notes": "Initial receipt"}
            ],
        },
        # SNS-TEMP-PT100 (at/below min stock in DEL)
        {
            "part_code": "SNS-TEMP-PT100",
            "loc_code": "DEL",
            "quantity": 1,
            "min_stock_level": 3,
            "store_name": "Delhi Spares Room",
            "rack": "E02",
            "bin": "B06",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 1, "after": 1, "user": admin, "delta_days": 10, "notes": "Single sensor remaining"}
            ],
        },
        {
            "part_code": "SNS-TEMP-PT100",
            "loc_code": "PNQ",
            "quantity": 4,
            "min_stock_level": 2,
            "store_name": "Central Spares",
            "rack": "E03",
            "bin": "B07",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 4, "after": 4, "user": admin, "delta_days": 10, "notes": "Initial receipt"}
            ],
        },
        # GSK-FLG-DN50
        {
            "part_code": "GSK-FLG-DN50",
            "loc_code": "BLR",
            "quantity": 25,
            "min_stock_level": 10,
            "store_name": "Mechanical Store",
            "rack": "R16",
            "bin": "B01",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 25, "after": 25, "user": admin, "delta_days": 19, "notes": "Bulk gasket pack"}
            ],
        },
        {
            "part_code": "GSK-FLG-DN50",
            "loc_code": "DEL",
            "quantity": 12,
            "min_stock_level": 5,
            "store_name": "Delhi Spares Room",
            "rack": "R04",
            "bin": "B02",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 12, "after": 12, "user": admin, "delta_days": 19, "notes": "Bulk gasket pack"}
            ],
        },
        # FUS-HRC-63A
        {
            "part_code": "FUS-HRC-63A",
            "loc_code": "BLR",
            "quantity": 30,
            "min_stock_level": 10,
            "store_name": "Electrical Store",
            "rack": "E05",
            "bin": "B01",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 30, "after": 30, "user": admin, "delta_days": 21, "notes": "Bussmann carton"}
            ],
        },
        {
            "part_code": "FUS-HRC-63A",
            "loc_code": "PNQ",
            "quantity": 15,
            "min_stock_level": 5,
            "store_name": "Central Spares",
            "rack": "E04",
            "bin": "B02",
            "history": [
                {"type": TransactionType.RECEIVED, "change": 15, "after": 15, "user": admin, "delta_days": 21, "notes": "Initial receipt"}
            ],
        },
    ]

    inv_created = 0
    inv_existing = 0
    tx_created = 0

    for item in inventory_plan:
        part = part_map[item["part_code"]]
        loc = location_map[item["loc_code"]]

        existing_inv = session.scalars(
            select(Inventory).where(
                Inventory.part_id == part.id,
                Inventory.location_id == loc.id,
            )
        ).first()

        if existing_inv:
            inv_existing += 1
            # Idempotent: don't recreate transactions for existing inventory
            continue

        # Create new inventory row
        new_inv = Inventory(
            part_id=part.id,
            location_id=loc.id,
            quantity=item["quantity"],
            min_stock_level=item["min_stock_level"],
            store_name=item["store_name"],
            rack=item["rack"],
            bin=item["bin"],
        )
        session.add(new_inv)
        session.flush()
        inv_created += 1

        # Create corresponding ledger history
        for tx_data in item["history"]:
            tx_time = now - timedelta(days=tx_data["delta_days"])
            tx = InventoryTransaction(
                part_id=part.id,
                location_id=loc.id,
                user_id=tx_data["user"].id if tx_data["user"] else None,
                transaction_type=tx_data["type"],
                quantity_change=tx_data["change"],
                quantity_after=tx_data["after"],
                notes=tx_data.get("notes"),
                created_at=tx_time,
            )
            session.add(tx)
            tx_created += 1

    session.flush()
    print(f"Inventory: {inv_created} created, {inv_existing} already existed.")
    print(f"Transactions: {tx_created} ledger rows created.")


def run_self_check(session: Session) -> None:
    """Validate that every inventory row's quantity equals SUM(quantity_change) and latest quantity_after."""
    print("Running inventory ledger consistency self-check...")
    inventory_items = session.scalars(select(Inventory)).all()
    if not inventory_items:
        raise ValueError("Self-check failed: No inventory records found.")

    mismatches: List[str] = []

    for item in inventory_items:
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
            mismatches.append(
                f"Inventory [ID: {item.id}, Part: {item.part_id}, Loc: {item.location_id}]: "
                f"No transactions found (quantity={item.quantity})"
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

    if mismatches:
        for err in mismatches:
            print(f"[FAIL] {err}", file=sys.stderr)
        raise ValueError(
            f"Self-check FAILED: Found {len(mismatches)} inventory-ledger mismatch(es)."
        )

    print(
        f"[OK] Self-check PASSED: All {len(inventory_items)} inventory rows are perfectly consistent with the ledger."
    )


def main() -> None:
    """Main entry point for development database seed script."""
    parser = argparse.ArgumentParser(
        description="Idempotent development seed script for Spare Parts Management & Discovery System."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing records before seeding.",
    )
    args = parser.parse_args()

    default_password = check_environment()

    print("=" * 60)
    print("SpareHub Development Database Seed Script")
    print(f"Reset mode: {'ENABLED' if args.reset else 'DISABLED'}")
    print("=" * 60)

    session = SessionLocal()
    try:
        with session.begin():
            if args.reset:
                reset_database(session)

            location_map = seed_locations(session)
            user_map = seed_users(session, location_map, default_password)
            machine_map = seed_machines(session, location_map)
            part_map = seed_spare_parts_and_links(session, machine_map)
            seed_inventory_and_transactions(
                session, location_map, part_map, user_map
            )
            run_self_check(session)

        print("=" * 60)
        print("Database seeding completed successfully inside a single transaction!")
        print("=" * 60)
    except Exception as exc:
        print(f"\n[ERROR] Database seeding failed and transaction rolled back: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()

