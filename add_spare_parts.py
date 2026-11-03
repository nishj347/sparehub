from app.db.session import SessionLocal
from app.models.spare_part import SparePart
from app.models.inventory import Inventory
from app.models.part_machine import PartMachine
from app.models.location import Location
from app.models.machine import Machine

db = SessionLocal()

def get_location(code):
    loc = db.query(Location).filter(Location.code.ilike(code)).first()
    if not loc:
        raise RuntimeError(f"Location not found: {code}")
    return loc

def get_machine(code):
    machine = db.query(Machine).filter(Machine.code == code).first()
    if not machine:
        raise RuntimeError(f"Machine not found: {code}")
    return machine

hwd = get_location("hwd")
blr = get_location("BLR")

machines = {
    code: get_machine(code)
    for code in [
        "C-14", "P-07", "M-03", "CT-11", "CP-02",
        "CL-05", "R-09", "D-04"
    ]
}

parts = [
    {
        "part_number": "BRG-6205",
        "name": "Bearing 6205-2RS",
        "category": "Bearing",
        "manufacturer": "SKF",
        "description": "Deep groove sealed ball bearing used in conveyor and packaging equipment.",
        "specifications": {"bore": "25 mm", "outer_diameter": "52 mm", "width": "15 mm", "seal": "2RS"},
        "machines": ["C-14", "P-07"],
        "hwd": (12, "Mechanical Store", "R14", "B07", 5),
        "blr": (6, "Mechanical Store", "R12", "B03", 5),
    },
    {
        "part_number": "BRG-6308",
        "name": "Bearing 6308-2Z",
        "category": "Bearing",
        "manufacturer": "FAG",
        "description": "Shielded deep groove ball bearing for mixer and rolling equipment.",
        "specifications": {"bore": "40 mm", "outer_diameter": "90 mm", "width": "23 mm", "shield": "2Z"},
        "machines": ["M-03", "R-09"],
        "hwd": (8, "Mechanical Store", "R14", "B08", 4),
        "blr": (4, "Mechanical Store", "R12", "B04", 3),
    },
    {
        "part_number": "CPL-L100",
        "name": "Jaw Coupling L100",
        "category": "Coupling",
        "manufacturer": "Lovejoy",
        "description": "Flexible jaw coupling for power transmission between motor and driven shaft.",
        "specifications": {"size": "L100", "material": "Aluminium", "element": "NBR"},
        "machines": ["C-14", "CP-02"],
        "hwd": (5, "Mechanical Store", "R09", "B03", 3),
        "blr": (2, "Mechanical Store", "R10", "B02", 2),
    },
    {
        "part_number": "BLT-A52",
        "name": "V-Belt A52",
        "category": "Belt",
        "manufacturer": "Gates",
        "description": "Industrial V-belt for compressor and dryer drive systems.",
        "specifications": {"section": "A", "length": "52 in", "construction": "Rubber"},
        "machines": ["CP-02", "D-04"],
        "hwd": (18, "Mechanical Store", "R09", "B05", 6),
        "blr": (8, "Mechanical Store", "R10", "B05", 5),
    },
    {
        "part_number": "BLT-B78",
        "name": "V-Belt B78",
        "category": "Belt",
        "manufacturer": "Fenner",
        "description": "Heavy-duty V-belt used on mixer drive assembly.",
        "specifications": {"section": "B", "length": "78 in", "construction": "Rubber"},
        "machines": ["M-03"],
        "hwd": (3, "Mechanical Store", "R09", "B06", 5),
        "blr": None,
    },
    {
        "part_number": "MTR-1HP",
        "name": "Induction Motor 1 HP",
        "category": "Motor",
        "manufacturer": "Siemens",
        "description": "Three-phase induction motor used for pump and packaging applications.",
        "specifications": {"power": "1 HP", "voltage": "415 V", "frequency": "50 Hz", "phase": "3"},
        "machines": ["CL-05", "P-07"],
        "hwd": (4, "Electrical Store", "E03", "B02", 3),
        "blr": (2, "Electrical Store", "E02", "B02", 2),
    },
    {
        "part_number": "SEL-MS35",
        "name": "Mechanical Seal 35 mm",
        "category": "Seal",
        "manufacturer": "John Crane",
        "description": "Mechanical shaft seal for cooling pump assembly.",
        "specifications": {"shaft_diameter": "35 mm", "material": "Carbon/Ceramic"},
        "machines": ["CL-05"],
        "hwd": (7, "Spares Cage", "S01", "B04", 3),
        "blr": None,
    },
    {
        "part_number": "FLT-AF200",
        "name": "Air Filter Element",
        "category": "Filter",
        "manufacturer": "Donaldson",
        "description": "Replacement air filter element for compressor system.",
        "specifications": {"type": "Air Filter", "diameter": "200 mm", "media": "Synthetic"},
        "machines": ["CP-02"],
        "hwd": (10, "Spares Cage", "S01", "B06", 4),
        "blr": (3, "Spares Cage", "S02", "B03", 2),
    },
    {
        "part_number": "SNS-PX18",
        "name": "Proximity Sensor M18",
        "category": "Sensor",
        "manufacturer": "Omron",
        "description": "Inductive proximity sensor for machine position and object detection.",
        "specifications": {"diameter": "M18", "type": "Inductive", "voltage": "10-30 VDC"},
        "machines": ["P-07", "CT-11"],
        "hwd": (6, "Electrical Store", "E03", "B05", 3),
        "blr": (3, "Electrical Store", "E02", "B05", 2),
    },
    {
        "part_number": "GSK-FL100",
        "name": "Flange Gasket DN100",
        "category": "Gasket",
        "manufacturer": "Garlock",
        "description": "Industrial flange gasket for cooling and dryer piping connections.",
        "specifications": {"size": "DN100", "material": "Compressed Fibre", "pressure_class": "PN16"},
        "machines": ["CL-05", "D-04"],
        "hwd": (2, "Spares Cage", "S01", "B08", 5),
        "blr": (5, "Spares Cage", "S02", "B04", 3),
    },
    {
        "part_number": "FUS-16A",
        "name": "HRC Fuse 16A",
        "category": "Fuse",
        "manufacturer": "Schneider Electric",
        "description": "High rupturing capacity fuse for industrial electrical protection.",
        "specifications": {"current": "16 A", "type": "HRC", "voltage": "415 V"},
        "machines": ["M-03", "R-09"],
        "hwd": (25, "Electrical Store", "E03", "B07", 10),
        "blr": (12, "Electrical Store", "E02", "B07", 8),
    },
    {
        "part_number": "CHN-RC08",
        "name": "Roller Chain 08B",
        "category": "Chain",
        "manufacturer": "Renold",
        "description": "Industrial roller chain used in conveyor drive transmission.",
        "specifications": {"size": "08B", "pitch": "12.7 mm", "type": "Simplex"},
        "machines": ["C-14"],
        "hwd": (9, "Mechanical Store", "R10", "B02", 4),
        "blr": (4, "Mechanical Store", "R11", "B02", 3),
    },
    {
        "part_number": "SPR-C14",
        "name": "Conveyor Drive Sprocket",
        "category": "Sprocket",
        "manufacturer": "Renold",
        "description": "Drive sprocket for conveyor chain transmission.",
        "specifications": {"chain_size": "08B", "teeth": 18, "bore": "25 mm"},
        "machines": ["C-14"],
        "hwd": (2, "Mechanical Store", "R10", "B04", 3),
        "blr": None,
    },
    {
        "part_number": "SNS-PT100",
        "name": "Temperature Sensor PT100",
        "category": "Sensor",
        "manufacturer": "WIKA",
        "description": "RTD temperature sensor for process temperature monitoring.",
        "specifications": {"type": "PT100", "range": "-50 to 250 C", "probe": "150 mm"},
        "machines": ["P-07", "D-04"],
        "hwd": (0, "Electrical Store", "E03", "B09", 2),
        "blr": (4, "Electrical Store", "E02", "B09", 2),
    },
]

created_parts = 0
created_inventory = 0
created_links = 0

for data in parts:
    part = db.query(SparePart).filter(SparePart.part_number == data["part_number"]).first()

    if not part:
        part = SparePart(
            part_number=data["part_number"],
            name=data["name"],
            category=data["category"],
            manufacturer=data["manufacturer"],
            description=data["description"],
            specifications=data["specifications"],
            is_active=True,
        )
        db.add(part)
        db.flush()
        created_parts += 1
    else:
        print(f"SKIP PART: {data['part_number']} already exists")

    for machine_code in data["machines"]:
        machine = machines[machine_code]
        existing_link = db.query(PartMachine).filter(
            PartMachine.part_id == part.id,
            PartMachine.machine_id == machine.id
        ).first()

        if not existing_link:
            db.add(PartMachine(
                part_id=part.id,
                machine_id=machine.id,
            ))
            created_links += 1

    for location, stock in [(hwd, data["hwd"]), (blr, data["blr"])]:
        if stock is None:
            continue

        quantity, store_name, rack, bin_name, min_stock = stock

        inventory = db.query(Inventory).filter(
            Inventory.part_id == part.id,
            Inventory.location_id == location.id
        ).first()

        if not inventory:
            db.add(Inventory(
                part_id=part.id,
                location_id=location.id,
                quantity=quantity,
                store_name=store_name,
                rack=rack,
                bin=bin_name,
                min_stock_level=min_stock,
            ))
            created_inventory += 1
        else:
            print(
                f"SKIP INVENTORY: {data['part_number']} @ {location.code} already exists"
            )

db.commit()

print()
print("========================================")
print("SPARE PART DEMO DATA CREATED")
print("========================================")
print(f"Parts created:             {created_parts}")
print(f"Inventory records created: {created_inventory}")
print(f"Machine links created:     {created_links}")
print(f"Haridwar location:         {hwd.name} ({hwd.code})")
print(f"Bengaluru location:        {blr.name} ({blr.code})")
print("========================================")

db.close()
