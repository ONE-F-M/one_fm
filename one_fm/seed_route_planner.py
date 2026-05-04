"""
Generate test data for the Route Planner page.

Run with:
    bench execute one_fm.seed_route_planner.run
"""
import frappe
from frappe.utils import now_datetime

# Kuwait coordinates for transport stops
TRANSPORT_STOPS = [
    {"name": "TS-Mahboula",   "label": "Mahboula Transport Stop",   "lat": 29.1499, "lng": 48.1232},
    {"name": "TS-Farwaniya",  "label": "Farwaniya Transport Stop",  "lat": 29.2827, "lng": 47.9584},
    {"name": "TS-Mangaf",     "label": "Mangaf Transport Stop",     "lat": 29.1423, "lng": 48.1301},
]

ACC_STOP_MAP = {
    "Mahboula 3":            "TS-Mahboula",
    "Mahboula 12":           "TS-Mahboula",
    "Mahboula 13":           "TS-Mahboula",
    "Mahboula 15":           "TS-Mahboula",
    "Farwaniya Apartments":  "TS-Farwaniya",
    "Farwaniya 171":         "TS-Farwaniya",
    "Mangaf 38":             "TS-Mangaf",
}

DEPOT = {"name": "TS-Depot", "label": "Vehicle Depot - Shuwaikh", "lat": 29.3375, "lng": 47.9366}


def _ensure_location(name, label, lat, lng):
    """Create a Location record, or update it if it already exists."""
    if frappe.db.exists("Location", name):
        print(f"  Location '{name}' exists, updating coords")
        frappe.db.set_value("Location", name, {
            "latitude": lat, "longitude": lng
        })
        return
    doc = frappe.get_doc({
        "doctype": "Location",
        "location_name": label,
        "latitude": lat,
        "longitude": lng,
        "geofence_radius": 100,
    })
    doc.insert(ignore_permissions=True)
    # Rename to our desired key if autoname gave something else
    if doc.name != name:
        frappe.rename_doc("Location", doc.name, name, force=True)
    print(f"  ✅ Created Location: {name}")


def _ensure_vehicle(label, seats, make, depot_name):
    """Create a Vehicle if it doesn't exist."""
    if frappe.db.exists("Vehicle", {"license_plate": label}):
        print(f"  Vehicle '{label}' exists, skipping")
        return

    # Need a driver employee — pick any active one
    driver = frappe.db.get_value("Employee", {"status": "Active"}, "name")
    if not driver:
        print(f"  ⚠ No active employee for driver, skipping vehicle {label}")
        return

    doc = frappe.get_doc({
        "doctype": "Vehicle",
        "license_plate": label,
        "make": make,
        "model": make,
        "last_odometer": 0,
        "acquisition_date": "2025-01-01",
        "location": depot_name,
        "seats": seats,
        "transport_stop_vehicle": 1,
        "employee": driver,
        "fuel_type": "Diesel",
        "uom": "Liter",
        "one_fm_vehicle_category": frappe.db.get_all("Vehicle Category", limit=1, pluck="name")[0] if frappe.db.count("Vehicle Category") else None,
        "one_fm_vehicle_type": frappe.db.get_all("Vehicle Type", limit=1, pluck="name")[0] if frappe.db.count("Vehicle Type") else None,
    })
    try:
        doc.flags.ignore_validate = True
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        print(f"  ✅ Created Vehicle: {label} ({seats} seats)")
    except Exception as e:
        # Fallback: direct SQL insert for minimal record
        print(f"  ⚠ ORM insert failed ({e}), using direct SQL")
        frappe.db.sql("""
            INSERT INTO `tabVehicle` (name, license_plate, make, model,
                last_odometer, location, seats, transport_stop_vehicle,
                employee, fuel_type, uom, owner, creation, modified, modified_by, docstatus)
            VALUES (%(name)s, %(lp)s, %(make)s, %(make)s,
                0, %(loc)s, %(seats)s, 1,
                %(driver)s, 'Diesel', 'Liter', 'Administrator',
                NOW(), NOW(), 'Administrator', 0)
        """, {
            "name": label, "lp": label, "make": make,
            "loc": depot_name, "seats": seats, "driver": driver
        })
        print(f"  ✅ Created Vehicle (SQL): {label} ({seats} seats)")


def run():
    print("=" * 60)
    print("SEEDING ROUTE PLANNER TEST DATA")
    print("=" * 60)

    # ── 1. Create Location records ──
    print("\n1. Creating transport stop locations...")
    for stop in TRANSPORT_STOPS + [DEPOT]:
        _ensure_location(stop["name"], stop["label"], stop["lat"], stop["lng"])
    frappe.db.commit()

    # ── 2. Set transport_stop_location on Accommodations ──
    print("\n2. Linking accommodations to transport stops...")
    accommodations = frappe.get_all("Accommodation", fields=["name", "accommodation"])
    for acc in accommodations:
        stop_name = ACC_STOP_MAP.get(acc.accommodation)
        if not stop_name:
            print(f"  ⚠ No mapping for: {acc.accommodation}")
            continue
        frappe.db.set_value("Accommodation", acc.name, "transport_stop_location", stop_name)
        print(f"  ✅ {acc.name} ({acc.accommodation}) → {stop_name}")
    frappe.db.commit()

    # ── 3. Create Vehicles ──
    print("\n3. Creating transport vehicles...")
    vehicles_data = [
        {"label": "BUS-01", "seats": 50, "make": "Toyota Coaster"},
        {"label": "BUS-02", "seats": 50, "make": "Toyota Coaster"},
        {"label": "VAN-01", "seats": 14, "make": "Toyota HiAce"},
        {"label": "VAN-02", "seats": 14, "make": "Toyota HiAce"},
    ]
    for v in vehicles_data:
        _ensure_vehicle(v["label"], v["seats"], v["make"], DEPOT["name"])
    frappe.db.commit()

    # ── 4. Create Checkin records ──
    print("\n4. Creating employee checkin records...")
    active_shifts = frappe.get_all("Operations Shift",
        filters={"status": "Active"}, fields=["name"])
    shift_names = [s.name for s in active_shifts]

    employees = frappe.get_all("Employee",
        filters={"status": "Active", "shift": ["in", shift_names]},
        fields=["name", "employee_name", "shift"],
        limit=80
    )

    acc_list = [a for a in accommodations if a.accommodation in ACC_STOP_MAP]
    created = 0
    for i, emp in enumerate(employees):
        exists = frappe.db.exists("Accommodation Checkin Checkout",
            {"employee": emp.name, "type": "IN"})
        if exists:
            continue

        acc = acc_list[i % len(acc_list)]
        doc = frappe.get_doc({
            "doctype": "Accommodation Checkin Checkout",
            "naming_series": "CHECKIN-.YYYY.-",
            "type": "IN",
            "employee": emp.name,
            "full_name": emp.employee_name,
            "accommodation": acc.name,
            "checkin_checkout_date_time": now_datetime(),
            "checked_out": 0,
            "new_or_current_resident": "New Resident",
        })
        try:
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            print(f"  ⚠ {emp.name}: {e}")

    frappe.db.commit()
    print(f"  ✅ Created {created} checkin records")

    # ── Summary ──
    print("\n" + "=" * 60)
    acc_count = frappe.db.count("Accommodation", {"transport_stop_location": ["is", "set"]})
    veh_count = frappe.db.sql("SELECT COUNT(*) FROM `tabVehicle` WHERE transport_stop_vehicle=1")[0][0]
    chk_count = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabAccommodation Checkin Checkout`
        WHERE type='IN' AND employee IS NOT NULL AND employee != ''
    """)[0][0]
    print(f"  Accommodations with stop: {acc_count}")
    print(f"  Transport vehicles:       {veh_count}")
    print(f"  Employee checkins:        {chk_count}")
    print("=" * 60)
    print("🎉 Done! Reload the Route Planner page.")
