import frappe
import requests
from frappe import _
from frappe.utils import cint
from one_fm.one_fm.doctype.transportation_manifest.manifest_sync import sync_manifest_details
from one_fm.one_fm.doctype.vehicle_handover_log.vehicle_handover_log import get_handover_windows
from one_fm.operations.doctype.route_plan.route_plan import _card_direction, card_rows
from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
    qoa_buffer_minutes,
)
from one_fm.overrides.vehicle import passenger_capacity

PICKUP_BUFFER = 10             # minutes
MAX_TRANSIT = 60               # minutes

def get_context(context):
    pass

@frappe.whitelist()
def get_route_planner_data():
    try:
        import pytz
        from datetime import timedelta

        # ── Time bounds ──
        tz_name = frappe.db.get_single_value("System Settings", "time_zone") or "UTC"
        site_tz = pytz.timezone(tz_name)
        local_today_start = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 00:00:00")) - timedelta(hours=3)
        local_today_end   = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 23:59:59")) + timedelta(hours=3)
        global_start_utc  = local_today_start.astimezone(pytz.utc).replace(tzinfo=None)
        global_end_utc    = local_today_end.astimezone(pytz.utc).replace(tzinfo=None)

        def fmt(dt):
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        def to_utc(dt_str):
            dt = frappe.utils.get_datetime(f"{frappe.utils.today()} {dt_str}")
            return site_tz.localize(dt).astimezone(pytz.utc).replace(tzinfo=None)

        # ── Coords cache (avoid repeated DB lookups for same Location) ──
        _coords_cache = {}
        def get_coords_cached(doctype, name):
            key = (doctype, name)
            if key not in _coords_cache:
                _coords_cache[key] = get_coords(doctype, name)
            return _coords_cache[key]

        # ── 1. Vehicles (batch queries) ──
        transport_vehicles = frappe.get_all("Vehicle",
            filters={"transport_stop_vehicle": 1},
            fields=["name", "license_plate", "location", "seats", "custom_max_passenger_capacity",
                    "custom_includes_driver_seat", "one_fm_vehicle_type", "make", "model", "employee",
                    "one_fm_vehicle_category"],
            order_by="name asc"
        )

        # Batch-fetch driver names in one query
        emp_ids_for_drivers = [v.employee for v in transport_vehicles if v.employee]
        driver_map = {}
        if emp_ids_for_drivers:
            for row in frappe.get_all("Employee",
                filters={"name": ["in", emp_ids_for_drivers]},
                fields=["name", "employee_name"]
            ):
                driver_map[row.name] = row.employee_name

        # Batch-fetch accommodation labels for vehicle locations in one query
        veh_locations = list({v.location for v in transport_vehicles if v.location})
        veh_acc_map = {}
        if veh_locations:
            for row in frappe.get_all("Accommodation",
                filters={"transport_stop_location": ["in", veh_locations]},
                fields=["transport_stop_location", "accommodation"]
            ):
                veh_acc_map[row.transport_stop_location] = row.accommodation

        MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

        vehicles = []
        for v in transport_vehicles:
            coords = get_coords_cached("Location", v.location)
            if not coords:
                continue

            driver_name = driver_map.get(v.employee, "—") if v.employee else "—"
            acc_name = veh_acc_map.get(v.location, v.location)
            if acc_name in MAHBOULA_LABELS:
                acc_name = "Mahboula Camp"

            vehicles.append({
                "id":            v.name,
                "label":         v.name,
                "license_plate": v.license_plate or "",
                # WI-001778: the lane header and the details panel identify a vehicle
                # as "<plate>, <model>", so the model rides along with the plate.
                "model":         v.model or "",
                "driver":        driver_name,
                "seats":         v.seats or 0,
                # WI-002000: the passenger limit the canvas holds a drop to. Whether
                # "seats" counts the driver is per vehicle, so the fleet record
                # answers it rather than the page assuming.
                "max_passenger_capacity": passenger_capacity(v.seats, v.custom_includes_driver_seat),
                "type":          v.one_fm_vehicle_type or "—",
                "make":          v.make or "—",
                "accommodation": acc_name,
                "location":      v.location,
                "coords":        {"lat": coords[0], "lng": coords[1]},
                "is_leased":     v.one_fm_vehicle_category == "Leased"
            })

        # ── 2. Shipment cards (materialized in the backend) ──
        # Cards are now generated by
        # shipment_generator.generate_transportation_shipments and stored as
        # Transportation Shipment records; we read them here instead of
        # recomputing the accommodation/shift demand on every page load.
        shipment_cards = _build_transportation_shipment_cards(
            fmt, to_utc, get_coords_cached, timedelta
        )

        # ── 3. Driver handover windows (WI-001577) ──
        # Who is actually driving each vehicle, and when. The canvas labels every block
        # with the driver holding the vehicle at that hour, falling back to the permanent
        # custodian outside every handover window.
        def local_to_utc_iso(dt):
            local_dt = site_tz.localize(frappe.utils.get_datetime(dt))
            return fmt(local_dt.astimezone(pytz.utc).replace(tzinfo=None))

        handover_windows = {}
        raw_windows = get_handover_windows(
            [v["id"] for v in vehicles],
            local_today_start.replace(tzinfo=None),
            local_today_end.replace(tzinfo=None),
        )
        for vehicle_id, windows in raw_windows.items():
            handover_windows[vehicle_id] = [
                {
                    "start":       local_to_utc_iso(w["start"]),
                    "end":         local_to_utc_iso(w["end"]),
                    "driver_name": w["driver_name"],
                }
                for w in windows
            ]

        return {
            "status":            "ok",
            "date":              frappe.utils.today(),
            "global_start":      fmt(global_start_utc),
            "global_end":        fmt(global_end_utc),
            "vehicles":          vehicles,
            "shipment_cards":    shipment_cards,
            # The driver's report-time buffer, so the block drawer can print QOA without
            # a second round trip (WI-002151 AC 1.2).
            "qoa_buffer_minutes": qoa_buffer_minutes(),
            "handover_windows":  handover_windows
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Route Planner Data Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def optimize_transportation_routes():
    try:
        config = frappe.get_single("Route Optimization API Configuration")
        if not config.enabled:
            frappe.msgprint(_("Route Optimization API is disabled in configuration."))
            return
            
        nested_map = get_grouped_employees_by_accommodation()
        
        if not nested_map:
            frappe.log_error("No active shifts or employees found for route optimization", "Route Optimization")
            return
            
        import pytz
        from datetime import timedelta
        site_tz = pytz.timezone(frappe.db.get_single_value("System Settings", "time_zone") or "UTC")
        local_today_start = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 00:00:00")) - timedelta(hours=3)
        local_today_end = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 23:59:59")) + timedelta(hours=3)
        
        global_start_utc = local_today_start.astimezone(pytz.utc).replace(tzinfo=None)
        global_end_utc = local_today_end.astimezone(pytz.utc).replace(tzinfo=None)
        global_bounds = (global_start_utc, global_end_utc)

        shipments, swap_keys, pair_labels, shipment_employees, shipment_site_locations, shipment_shift_names = build_shipments_from_nested_map(nested_map, config, global_bounds)

        results = process_accommodations(
            shipments,
            swap_keys,
            shipment_employees,
            shipment_site_locations,
            shipment_shift_names,
            pair_labels,
            global_bounds,
        )
        
        return results
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Route Optimization API Error")
        return {"status": "error", "message": str(e)}

def get_grouped_employees_by_accommodation() -> dict:
    # 1. Fetch all active Operations Shift entries
    active_shifts = frappe.get_all("Operations Shift", filters={"status": "Active"}, fields=["name", "site"])
    if not active_shifts:
        return {}

    shift_names = [s.name for s in active_shifts]

    # 2. Find all employees with a shift allocation matching one of the active shifts
    employees = frappe.get_all("Employee",
        filters={"status": "Active", "shift": ["in", shift_names]},
        fields=["name", "shift"]
    )
    if not employees:
        return {}

    emp_ids = [e.name for e in employees]
    emp_shift_map = {e.name: e.shift for e in employees}

    # 3. Bulk-fetch the latest IN checkin per employee (single query instead of N+1)
    #    Uses a correlated subquery to pick the most recent checkin per employee.
    checkin_rows = frappe.db.sql("""
        SELECT c.employee, c.accommodation
        FROM `tabAccommodation Checkin Checkout` c
        INNER JOIN (
            SELECT employee, MAX(creation) AS max_creation
            FROM `tabAccommodation Checkin Checkout`
            WHERE type = 'IN'
              AND employee IS NOT NULL
              AND employee != ''
              AND employee IN %(emp_ids)s
            GROUP BY employee
        ) latest ON c.employee = latest.employee AND c.creation = latest.max_creation
        WHERE c.type = 'IN'
    """, {"emp_ids": emp_ids}, as_dict=True)

    if not checkin_rows:
        # Log once instead of per-employee to avoid thousands of Error Log entries
        frappe.log_error(
            f"No employees (out of {len(emp_ids)}) have Accommodation Checkin Checkout (IN) records",
            "Route Optimization"
        )
        return {}

    # 4. Bulk-fetch accommodation labels
    acc_ids = list({r.accommodation for r in checkin_rows if r.accommodation})
    acc_labels = {}
    if acc_ids:
        for row in frappe.get_all("Accommodation",
            filters={"name": ["in", acc_ids]},
            fields=["name", "accommodation"]
        ):
            acc_labels[row.name] = row.accommodation

    MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

    # 5. Build accommodation → employees map
    accommodation_map = {}
    for row in checkin_rows:
        acc_id = row.accommodation
        acc_label = acc_labels.get(acc_id)
        if not acc_label:
            continue

        acc_key = "Mahboula Camp" if acc_label in MAHBOULA_LABELS else acc_id

        if acc_key not in accommodation_map:
            accommodation_map[acc_key] = {
                "lookup_id": acc_id,
                "employees": []
            }

        emp_name = row.employee
        if emp_name in emp_shift_map:
            accommodation_map[acc_key]["employees"].append(
                frappe._dict({"name": emp_name, "shift": emp_shift_map[emp_name]})
            )

    # 6. Filter to accommodations with transport_stop_location and group by shift
    acc_keys_to_check = list({d["lookup_id"] for d in accommodation_map.values()})
    acc_stop_map = {}
    if acc_keys_to_check:
        for row in frappe.get_all("Accommodation",
            filters={"name": ["in", acc_keys_to_check], "transport_stop_location": ["is", "set"]},
            fields=["name", "transport_stop_location"]
        ):
            acc_stop_map[row.name] = row.transport_stop_location

    nested_map = {}
    for acc_key, data in accommodation_map.items():
        lookup_id = data["lookup_id"]
        if lookup_id not in acc_stop_map:
            continue

        nested_map[acc_key] = {
            "lookup_id": lookup_id,
            "shifts": {}
        }
        for emp in data["employees"]:
            shift = emp.shift
            if shift not in nested_map[acc_key]["shifts"]:
                nested_map[acc_key]["shifts"][shift] = []
            nested_map[acc_key]["shifts"][shift].append(emp.name)

    return nested_map


def build_shipments_from_nested_map(nested_map: dict, config: object, global_bounds: tuple) -> tuple:
    shipments_by_accommodation = {}
    all_swap_keys = []
    all_pair_labels = []
    all_shipment_employees = {}
    all_shipment_site_locations = {} 
    all_shipment_shift_names = {}

    pickup_window_buffer = 10
    penalty_cost = config.penalty_cost or 1000000

    for acc_name, data in nested_map.items():
        shipments = []
        lookup_id = data["lookup_id"]
        shifts_dict = data["shifts"]
        
        acc_coords = get_coords("Accommodation", lookup_id)
        if not acc_coords:
            continue

        olm_groups = {}

        for shift_name, employee_list in shifts_dict.items():
            shift_doc = frappe.get_doc("Operations Shift", shift_name)
            operations_site = shift_doc.site
            headcount = len(employee_list)

             # ── Resolve site location label from Operations Site ──
            site_location = frappe.db.get_value("Operations Site", operations_site, "site_location") or operations_site

            one_site_many_locations = frappe.get_all("Site Transport Stop Location",
                filters={"site_arrangement": "One Site Many Locations", "site": operations_site},
                fields=["name"]
            )

            all_osm_locations = []
            for osm in one_site_many_locations:
                osm_doc = frappe.get_doc("Site Transport Stop Location", osm.name)
                for row in osm_doc.transport_stop_locations:
                    coords = get_coords("Location", row.location)
                    if coords:
                        all_osm_locations.append({"name": row.location, "coords": coords})

            if all_osm_locations:
                num_locs = len(all_osm_locations)
                base_h = headcount // num_locs
                extra_h = headcount % num_locs
                emp_idx  = 0

                for i, loc in enumerate(all_osm_locations):
                    current_h = base_h + (1 if i < extra_h else 0)
                    loc_employees = employee_list[emp_idx:emp_idx + current_h]
                    emp_idx      += current_h                                    
                    if current_h > 0:
                        shipments.extend(create_shipment_pair(
                            acc_name, shift_doc, loc["name"], acc_coords, loc["coords"],
                            current_h, pickup_window_buffer, penalty_cost, global_bounds,
                            swap_keys_out=all_swap_keys,
                            pair_labels_out=all_pair_labels,
                            employees_out=all_shipment_employees,
                            employee_list=loc_employees,
                            site_location_out=all_shipment_site_locations, 
                            site_location=site_location,             
                            shift_name_out=all_shipment_shift_names
                        ))

            one_location_many_sites = frappe.db.sql("""
                SELECT parent FROM `tabLocation To Site Mapping` WHERE sites = %s
            """, (operations_site,), as_dict=True)

            for olm in one_location_many_sites:
                olm_doc = frappe.get_doc("Site Transport Stop Location", olm.parent)
                if olm_doc.site_arrangement != "One Location Many Sites":
                    continue
                
                stop_location = olm_doc.transport_stop_location
                start_dt = frappe.utils.get_datetime(f"2000-01-01 {shift_doc.start_time}")
                time_key = start_dt.hour
                
                group_key = (stop_location, time_key)
                if group_key not in olm_groups:
                    olm_groups[group_key] = {"shifts": [], "headcount": 0, "employees": []}
                
                olm_groups[group_key]["shifts"].append(shift_doc)
                olm_groups[group_key]["headcount"] += headcount
                olm_groups[group_key]["employees"].extend(employee_list)

        for group_key, data in olm_groups.items():
            stop_location, time_key = group_key
            stop_coords = get_coords("Location", stop_location)
            if not stop_coords:
                continue
            
            shifts = data["shifts"]

             # ── Use actual shift names instead of pseudo name ──
            real_shift_names = " · ".join(sorted(set(s.name for s in shifts)))

            # ── Resolve all site locations for this group ──
            site_locations = list({
                frappe.db.get_value("Operations Site", s.site, "site_location") or s.site
                for s in shifts
            })
            site_location_str = " · ".join(sorted(site_locations))

            earliest_start = min(s.start_time for s in shifts)
            latest_end = max(s.end_time for s in shifts)
            pseudo_shift = frappe._dict({
                "name": f"Grouped_{stop_location}_{time_key}",
                "start_time": earliest_start,
                "end_time": latest_end
            })
            
            shipments.extend(create_shipment_pair(
                acc_name, pseudo_shift, stop_location, acc_coords, stop_coords,
                data["headcount"], pickup_window_buffer, penalty_cost, global_bounds,
                swap_keys_out=all_swap_keys,
                pair_labels_out=all_pair_labels,
                employees_out=all_shipment_employees,
                employee_list=data["employees"],
                site_location_out=all_shipment_site_locations, 
                site_location=site_location_str ,
                shift_name_out=all_shipment_shift_names,
                shift_name_override=real_shift_names             
            ))

        all_tuples = sorted(shipments, key=lambda x: x[1])
        
        batches = []
        if all_tuples:
            current_batch = [all_tuples[0][0]]
            for i in range(1, len(all_tuples)):
                prev_time = all_tuples[i-1][1]
                curr_time = all_tuples[i][1]
                
                from datetime import timedelta
                if curr_time - prev_time > timedelta(hours=2):
                    batches.append(current_batch)
                    current_batch = [all_tuples[i][0]]
                else:
                    current_batch.append(all_tuples[i][0])
            batches.append(current_batch)
            
        shipments_by_accommodation[acc_name] = batches
    
    all_emp_ids  = {eid for emps in all_shipment_employees.values() for eid in emps}
    emp_name_map = {
        e.name: {"employee_name": e.employee_name, "cell_number": e.cell_number or ""}
        for e in frappe.get_all("Employee",
            filters={"name": ["in", list(all_emp_ids)]},
            fields=["name", "employee_name", "cell_number"]
        )
    }
    shipment_employees_named = {
        label: [
            {"name": emp_name_map.get(eid, {}).get("employee_name", eid), "mobile": emp_name_map.get(eid, {}).get("cell_number", "")}
            for eid in eids
        ]
        for label, eids in all_shipment_employees.items()
    }

    return shipments_by_accommodation, all_swap_keys, all_pair_labels, shipment_employees_named, all_shipment_site_locations, all_shipment_shift_names

def create_shipment_pair(acc_name, shift, stop_location, acc_coords, stop_coords,
                          headcount, pickup_window_buffer, penalty_cost, global_bounds,
                          swap_keys_out=None, pair_labels_out=None, 
                          employees_out=None, employee_list=None,
                          site_location_out=None, site_location=None, shift_name_out=None,  shift_name_override=None):
    from frappe.utils import get_datetime
    from datetime import timedelta
    import pytz

    global_start, global_end = global_bounds

    def to_utc(dt_str):
        dt = get_datetime(f"{frappe.utils.today()} {dt_str}")
        site_tz = pytz.timezone(frappe.db.get_single_value("System Settings", "time_zone") or "UTC")
        dt_local = site_tz.localize(dt)
        return dt_local.astimezone(pytz.utc).replace(tzinfo=None)

    start_time_utc = to_utc(shift.start_time)
    end_time_utc = to_utc(shift.end_time)

    def fmt(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    shipment_base = {
        "loadDemands": {"seats": {"amount": headcount}},
        "penaltyCost": penalty_cost
    }

    boarding_duration = f"{max(headcount * 5, 30)}s"

    shipments = []

    expected_arrival = getattr(shift, "expected_arrival_time_at_site", None)
    if expected_arrival and str(expected_arrival) != str(shift.start_time):
        effective_start_utc = to_utc(expected_arrival)
        outbound_start = effective_start_utc   # buffer already baked in — use as-is
        outbound_end   = effective_start_utc
    else:
        effective_start_utc = start_time_utc
        outbound_start = start_time_utc - timedelta(minutes=PICKUP_BUFFER)
        outbound_end   = start_time_utc

    # ── OUTBOUND ─────────────────────────────────────────────────────────────
    # Employees must arrive at site by shift start_time.
    outbound_pickup_hard_start = outbound_start - timedelta(minutes=MAX_TRANSIT)

    if outbound_start < global_start: outbound_start = global_start
    if outbound_end > global_end: outbound_end = global_end

    outbound_swap_key = f"{stop_location}_{outbound_end.strftime('%H')}00_OUT"
    return_swap_key_pair = f"{stop_location}_{outbound_end.strftime('%H')}00_RET"
    outbound_label = f"{acc_name}_{shift.name}_{stop_location}_OUTBOUND"

    outbound = shipment_base.copy()
    outbound.update({
        "label": outbound_label,
        "shipmentType": outbound_swap_key,
        "pickups": [{
            "arrivalLocation": {"latitude": acc_coords[0], "longitude": acc_coords[1]},
            "timeWindows": [{
                "startTime": fmt(outbound_pickup_hard_start)
            }],
            "duration": boarding_duration
        }],
        "deliveries": [{
            "arrivalLocation": {"latitude": stop_coords[0], "longitude": stop_coords[1]},
            "duration": boarding_duration,
            "timeWindows": [{
                "softStartTime": fmt(outbound_start),
                "startTime":     fmt(outbound_start),
                "softEndTime":   fmt(outbound_end),
                "costPerHourBeforeSoftStartTime": 10000, # to prevent idling
                "costPerHourAfterSoftEndTime":    10000, # to prevent idling
            }]
        }]
    })
    if swap_keys_out is not None:
        swap_keys_out.append((outbound_swap_key, return_swap_key_pair))

    shipments.append((outbound, effective_start_utc))


    # ── RETURN ────────────────────────────────────────────────────────────────
    # Employees leave the site after shift end_time.
    return_start = end_time_utc
    return_end = end_time_utc + timedelta(minutes=PICKUP_BUFFER)
    return_delivery_hard_end = return_start + timedelta(minutes=MAX_TRANSIT)

    if return_start < global_start: return_start = global_start
    if return_end > global_end: return_end = global_end

    return_swap_key = f"{stop_location}_{return_start.strftime('%H')}00_RET"
    outbound_swap_key_pair = f"{stop_location}_{return_start.strftime('%H')}00_OUT"
    return_label = f"{acc_name}_{shift.name}_{stop_location}_RETURN"

    SITE_PICKUP_DEADLINE_MINUTES = 20
    return_pickup_hard_end = return_start + timedelta(minutes=SITE_PICKUP_DEADLINE_MINUTES)

    ret = shipment_base.copy()
    ret.update({
        "label": return_label,
        "shipmentType": return_swap_key,
        "pickups": [{
            "arrivalLocation": {"latitude": stop_coords[0], "longitude": stop_coords[1]},
            "timeWindows": [{
                "startTime":   fmt(return_start),
                "endTime":     fmt(return_pickup_hard_end),
                "softEndTime": fmt(return_end),
                "costPerHourAfterSoftEndTime": 1500
            }],
            "duration": boarding_duration
        }],
        "deliveries": [{
            "arrivalLocation": {"latitude": acc_coords[0], "longitude": acc_coords[1]},
            "duration": boarding_duration,
            "timeWindows": [{
                "endTime": fmt(return_delivery_hard_end)
            }]
        }]
    })
    if swap_keys_out is not None:
        swap_keys_out.append((outbound_swap_key_pair, return_swap_key))
    shipments.append((ret, end_time_utc))

    if pair_labels_out is not None:
        pair_labels_out.append((outbound_label, return_label))

    if employees_out is not None and employee_list is not None:
        employees_out[outbound_label] = employee_list
        employees_out[return_label]   = employee_list
    
    if site_location_out is not None and site_location is not None:
        site_location_out[outbound_label] = site_location
        site_location_out[return_label]   = site_location
    
    if shift_name_out is not None:
        shift_name_out[outbound_label] = shift.name
        shift_name_out[return_label]   = shift.name
    
    if shift_name_out is not None:
        display_shift_name = shift_name_override or shift.name
        shift_name_out[outbound_label] = display_shift_name
        shift_name_out[return_label]   = display_shift_name

    return shipments

def get_coords(doctype: str, name: str) -> tuple | None:
    """
    Returns (latitude, longitude) for a given record.
    
    - For "Accommodation": follows the transport_stop_location link to a Location
      record and retrieves its latitude/longitude directly.
    - For "Location": reads the latitude and longitude fields directly on the record.
    """

    if doctype == "Accommodation":
        # Follow the transport_stop_location link field to get the actual Location record
        stop_location = frappe.db.get_value("Accommodation", name, "transport_stop_location")
        if not stop_location:
            return None
        # Recursively resolve the Location record's coordinates
        return get_coords("Location", stop_location)

    elif doctype == "Location":
        lat, lng = frappe.db.get_value("Location", name, ["latitude", "longitude"])
        if lat and lng:
            return float(lat), float(lng)

    return None

def process_accommodations(shipments_dict: dict, swap_keys: set, shipment_employees, shipment_site_locations, shipment_shift_names, pair_labels,
                           global_bounds: tuple) -> list:
    results = []
    global_start_utc, global_end_utc = global_bounds
    
    all_shipments = []
    all_vehicles, vehicle_meta = build_vehicle_list(global_bounds)

    for acc_name, batches in shipments_dict.items():
        for shipments in batches:
            all_shipments.extend(shipments)
    
    # ── Add one rest shipment per vehicle ────────────────────────────────
    rest_shipments = build_rest_shipments(all_vehicles, global_bounds)
    all_shipments.extend(rest_shipments)

    if not all_shipments or not all_vehicles:
        return results

    present_types = {s["shipmentType"] for s in all_shipments if "shipmentType" in s}

    seen_pairs = set()
    swap_requirements = []

    for out_key, ret_key in swap_keys:
        pair = (out_key, ret_key)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        if out_key not in present_types or ret_key not in present_types:
            continue

        swap_requirements.append({
            "requiredShipmentTypeAlternatives": [ret_key],
            "dependentShipmentTypes": [out_key],
            "requirementMode": "PERFORMED_BY_SAME_VEHICLE"
        })

    payload = {
        "model": {
            "shipments": all_shipments,
            "vehicles": all_vehicles,
            "shipmentTypeRequirements": swap_requirements,
            "globalStartTime": global_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "globalEndTime": global_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }

    response = call_route_optimization_api(payload)

    return response

def build_rest_shipments(vehicles: list, global_bounds: tuple) -> list:
    """
    Creates one mandatory rest shipment per vehicle, tied to that vehicle
    exclusively via allowedVehicleIndices. The optimizer decides where in
    the day to slot the rest — it will always be at the vehicle's depot
    (accommodation) since that's the only location given.
    """
    global_start_utc, global_end_utc = global_bounds
    rest_shipments = []

    for i, vehicle in enumerate(vehicles):
        depot_location = vehicle.get("startLocation")
        if not depot_location:
            continue

        rest_shipments.append({
            "label": f"{vehicle['label']}_REST",
            "loadDemands": {"seats": {"amount": 0}},
            "penaltyCost": 9999999,          # effectively mandatory
            "allowedVehicleIndices": [i],     # binds rest to this vehicle only
            "pickups": [{
                "arrivalLocation": depot_location,
                "duration": "18000s",         # 5 hours
                "timeWindows": [{
                    "startTime": global_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "endTime":   global_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                }]
            }]
        })

    return rest_shipments

def build_vehicle_list(global_bounds: tuple) -> tuple: 
    config = frappe.get_single("Route Optimization API Configuration")
    global_start_utc, global_end_utc = global_bounds

    transport_vehicles = frappe.get_all("Vehicle",
        filters={"transport_stop_vehicle": 1},
        fields=["name", "location", "seats", "custom_includes_driver_seat",
                "one_fm_vehicle_type", "make", "employee"],
        order_by="name asc"
    )

    vehicles = []
    vehicle_meta = {}
    today_start = global_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    today_end   = global_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    for v in transport_vehicles:
        coords = get_coords("Location", v.location)
        if not coords:
            continue

        start_end_coords = {"latitude": coords[0], "longitude": coords[1]}

        MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

        acc_name = frappe.db.get_value("Accommodation", 
            {"transport_stop_location": v.location}, 
            "accommodation"
            ) or v.location   # fallback to raw location name if no match
        
        if acc_name in MAHBOULA_LABELS:
            acc_name = "Mahboula Camp"

        vehicles.append({
            "label": v.name,
            "startLocation": start_end_coords,
            "endLocation":   start_end_coords,
            "loadLimits":    {"seats": {"maxLoad": max(passenger_capacity(v.seats, v.custom_includes_driver_seat), 1)}},
            "startTimeWindows": [{"startTime": today_start}],
            "endTimeWindows":   [{"endTime":   today_end}],
            "fixedCost":        config.fixed_cost or 0,
            "costPerKilometer": config.cost_per_kilometer or 0,
            "costPerHour":      config.cost_per_hour or 0,
            "travelMode":       "DRIVING"
        })

        driver_name = "—"
        if v.employee:
            driver_name = frappe.db.get_value("Employee", v.employee, "employee_name") or "—"

        vehicle_meta[v.name] = {
            "type":   v.one_fm_vehicle_type or "—",
            "make":   v.make or "—",
            "seats":  v.seats or "—",
            "driver": driver_name,
            "location":      v.location or "—",
            "accommodation": acc_name 
        }

    return vehicles, vehicle_meta

def call_route_optimization_api(payload: dict) -> dict | None:
    try:
        # Get credentials from a secure place or site_config
        api_key = frappe.conf.get("google_route_optimization_api_key")
        project_id = frappe.conf.get("google_project_id")
        
        if not api_key or not project_id:
            frappe.log_error("Google API Key or Project ID missing in site_config", "Route Optimization")
            return {"status": "error", "message": "Credentials missing"}

        url = f"https://routeoptimization.googleapis.com/v1/projects/{project_id}:optimizeTours"
        
        headers = {
            "X-Goog-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Route Optimization API Call Failed")
        return None


# ── Persistence: save / load route planner assignments (DocType-based) ─────

def _route_plan_exists():
    """Check if Route Plan DocType has been migrated."""
    try:
        return frappe.db.exists("DocType", "Route Plan") and frappe.db.exists("DocType", "Route Plan Assignment")
    except Exception:
        return False


@frappe.whitelist()
def get_route_plans():
    """Return all Route Plans for the plan selector dropdown."""
    if not _route_plan_exists():
        return []
    plans = frappe.get_list("Route Plan",
        fields=["name", "title", "status", "effective_from", "effective_until", "is_default"],
        order_by="creation desc"
    )
    return plans


SHIPMENT_CARD_PREFIX = "TSHIP-"


def _build_transportation_shipment_cards(fmt, to_utc, get_coords_cached, timedelta):
    """Return draggable cards for Transportation Shipment records.

    Each shipment renders as a single compact card (one per shipment) exposing
    the fields the pool template and placement logic consume: headcount, its
    routing-type badge, destination and a time window. Card ids are namespaced
    with ``TSHIP-`` so save_assignments can flip the shipment to Assigned when
    the card is dropped on a vehicle.

    Both Unassigned and Assigned shipments are returned: the frontend hides the
    Assigned ones from the pool via its ``assignedCards`` set, but keeps them in
    ``shipment_cards`` so placed blocks can still resolve their card (needed for
    trip chaining, block detail, and manifest building after a reload).
    """
    cards = []
    shipments = frappe.get_all(
        "Transportation Shipment",
        filters={"status": ["in", ["Unassigned", "Assigned"]]},
        fields=[
            "name", "accommodation", "accommodation_name", "operations_shift",
            # Every shift the card serves, for the OLM stops one card covers several of.
            "aggregated_shifts",
            "operations_site", "stop_location", "headcount", "trip_direction",
            "routing_type_badge", "start_time", "end_time", "from_date", "to_date",
            "source_doctype", "source_docname", "pair_group",
            # What the card's own riders do, which its live direction stops saying once
            # the card is merged (WI-002078).
            "pre_merge_trip_direction",
            # Lineage for a card that was split off a bigger one (WI-002170).
            "is_split_overflow", "split_root",
        ],
    )
    if not shipments:
        return cards

    ship_names = [s.name for s in shipments]
    emp_rows = frappe.get_all(
        "Transportation Shipment Employee",
        filters={"parent": ["in", ship_names], "parenttype": "Transportation Shipment"},
        fields=["parent", "employee_id", "employee_name", "cell_number"],
        order_by="idx asc",
    )

    # Flag which passengers are Rambo relievers (filling in for a shift) so the
    # canvas detail panel can label regular staff vs replacements (MA3-12 AC6).
    # Reliever status is a role-level attribute on the Employee master.
    reliever_ids = set()
    passenger_ids = list({row.employee_id for row in emp_rows if row.employee_id})
    if passenger_ids:
        reliever_ids = {
            e.name
            for e in frappe.get_all(
                "Employee",
                filters={"name": ["in", passenger_ids], "custom_is_rambo_reliever": 1},
                fields=["name"],
            )
        }

    emps_by_ship = {}
    for row in emp_rows:
        emps_by_ship.setdefault(row.parent, []).append({
            "id": row.employee_id,
            "name": row.employee_name or row.employee_id,
            "mobile": row.cell_number or "",
            "is_reliever": row.employee_id in reliever_ids,
        })

    # Fallback times for shipments without an Operations Shift (ad-hoc journeys).
    trq_names = list({
        s.source_docname for s in shipments
        if s.source_doctype == "Trip Request" and s.source_docname
    })
    trq_time_map = {}
    if trq_names:
        for trq in frappe.get_all(
            "Trip Request",
            filters={"name": ["in", trq_names]},
            fields=["name", "departure_time", "return_time"],
        ):
            trq_time_map[trq.name] = trq

    for s in shipments:
        try:
            employees = emps_by_ship.get(s.name, [])

            trq = trq_time_map.get(s.source_docname) if s.source_docname else None
            dep = s.start_time or (trq.departure_time if trq else None) or "06:00:00"
            ret = s.end_time or (trq.return_time if trq else None) or "18:00:00"

            dep_utc = to_utc(str(dep))
            ret_utc = to_utc(str(ret))
            # A night shift finishes the morning after it starts, so its end time is
            # legitimately earlier on the clock than its start. Reading that as a broken
            # window and replacing it with "start + 1 hour" is why a 19:00-07:00 shift
            # advertised a 20:00 finish on its card (WI-002161). The canvas is a rolling
            # 24h view of one day's runs — the 07:00 pickup and the 19:00 drop both belong
            # on it — so the end keeps its own time of day rather than rolling onto
            # tomorrow's date and off the axis. Only a shift with no length recorded at
            # all still needs a fallback.
            if ret_utc == dep_utc:
                ret_utc = dep_utc + timedelta(hours=1)

            stop_coords = get_coords_cached("Location", s.stop_location) if s.stop_location else None
            acc_coords = get_coords_cached("Accommodation", s.accommodation) if s.accommodation else None

            direction = _normalize_direction(s.trip_direction)
            # A merged card is drawn and grouped as MIXED, but the canvas still has to
            # know whether its own riders board or alight to walk a merged run leg by
            # leg. The same rule the Route Plan save uses, so the seat count the
            # operator sees on the lane is the one the save will judge them by.
            own_direction = _card_direction(s.trip_direction, s.pre_merge_trip_direction)
            badge = (s.routing_type_badge or "DIRECT").upper()
            destination = s.stop_location or s.operations_site or ""

            cards.append({
                "id":                    f"{SHIPMENT_CARD_PREFIX}{s.name}",
                "shipment":              s.name,
                "is_shipment_doc":       True,
                "accommodation":         s.accommodation_name or s.accommodation or "—",
                "accommodation_coords":  {"lat": acc_coords[0], "lng": acc_coords[1]} if acc_coords else None,
                # Every generated card comes from an Operations Shift; a card serving
                # several names them all rather than claiming to be ad-hoc.
                "shift_name":            s.operations_shift or s.aggregated_shifts or "Ad-hoc",
                "site":                  s.operations_site or "",
                "site_location":         destination,
                "stop_location":         s.stop_location or "",
                "stop_coords":           {"lat": stop_coords[0], "lng": stop_coords[1]} if stop_coords else None,
                "headcount":             s.headcount or len(employees),
                "employees":             employees,
                "return_employees":      [],
                "from_date":             str(s.from_date) if s.from_date else None,
                "to_date":               str(s.to_date) if s.to_date else None,
                "outbound_window_start": fmt(dep_utc - timedelta(minutes=PICKUP_BUFFER)),
                "outbound_window_end":   fmt(dep_utc),
                "return_window_start":   fmt(ret_utc),
                "return_window_end":     fmt(ret_utc + timedelta(minutes=PICKUP_BUFFER)),
                "shift_start":           fmt(dep_utc),
                "shift_end":             fmt(ret_utc),
                "type":                  badge,
                "direction":             direction,
                "own_direction":         own_direction,
                "pair_id":               f"{SHIPMENT_CARD_PREFIX}{s.pair_group}" if s.pair_group else f"{SHIPMENT_CARD_PREFIX}{s.name}",
                "shift_direction_label": "→ Outbound (To Site)" if direction == "OUTBOUND" else "← Return (From Site)",
                # AC 2.5: the pool marks a card that holds the staff who did not fit.
                "is_split_overflow": bool(s.is_split_overflow),
                "split_root": s.split_root or None,
            })
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Transportation Shipment Card Build Error")
            continue

    return cards


def _shipment_from_card_id(card_id: str) -> str:
    """Extract the Transportation Shipment name from a namespaced card id.

    Returns an empty string for cards that are not backed by a shipment doc.
    """
    if not card_id or not card_id.startswith(SHIPMENT_CARD_PREFIX):
        return ""
    name = card_id[len(SHIPMENT_CARD_PREFIX):]
    for suffix in ("_OUTBOUND", "_RETURN", "_OUT", "_RET"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


def _normalize_direction(value: str) -> str:
    """Collapse the direction vocabularies onto a single OUTBOUND/RETURN/MIXED flag.

    Shipment docs store ``trip_direction`` as "Outward"/"Return"/"Mixed"; the canvas
    swim items and Route Plan Assignment rows carry "OUTBOUND"/"RETURN"/"MIXED". Both
    map to the same flag so a companion match can validate direction across the
    vocabularies.

    MIXED is matched before the RETURN test rather than after it (WI-002071). The old
    two-way version answered "anything that is not a return is an outbound", so a
    merged card normalised to OUTBOUND: the canvas drew it orange instead of the merge
    colour, and the status sync compared a MIXED placement against an OUTBOUND
    shipment. A third direction has to be recognised, not defaulted.
    """
    flag = (value or "").strip().upper()
    if flag.startswith("MIX"):
        return "MIXED"
    return "RETURN" if flag.startswith("RET") else "OUTBOUND"


def _sync_shipment_statuses(items, previously_linked=None):
    """Reconcile Transportation Shipment status with the saved canvas state.

    Shipments placed on a vehicle become Assigned; shipments this plan carried
    before but no longer places revert to Unassigned. Uses db.set_value to
    update the status directly without re-running the shipment controller.

    A card is only counted as Assigned when the swim item's direction flag matches
    the shipment's own trip_direction. The outbound and return legs of one demand
    share a pair group (the trip_group hash), so this direction check keeps an
    outbound placement from ever flipping the paired return card to Assigned, and
    vice-versa — the two legs stay independently assignable to different vehicles
    (Multi-Day Lane Replication).
    """
    # Resolve each placed card to the direction(s) it was dropped in.
    placed_dirs_by_shipment = {}
    for item in items:
        name = _shipment_from_card_id(item.get("cardId", ""))
        if name:
            placed_dirs_by_shipment.setdefault(name, set()).add(
                _normalize_direction(item.get("direction", ""))
            )

    # Companion selection: a shipment is Assigned only when it exists AND the
    # direction it was placed in matches its own trip_direction (trip_group hash
    # AND direction flag — never one leg sweeping the other).
    assigned = set()
    if placed_dirs_by_shipment:
        shipment_dir = {
            row.name: _normalize_direction(row.trip_direction)
            for row in frappe.get_all(
                "Transportation Shipment",
                filters={"name": ["in", list(placed_dirs_by_shipment)]},
                fields=["name", "trip_direction"],
            )
        }
        mismatched = []
        for name, placed_dirs in placed_dirs_by_shipment.items():
            own_dir = shipment_dir.get(name)
            if own_dir is None:
                continue  # shipment vanished between save and sync
            if own_dir in placed_dirs:
                assigned.add(name)
            else:
                mismatched.append(
                    f"{name}: placed as {sorted(placed_dirs)}, shipment says {own_dir}"
                )

        if mismatched:
            # One entry per save rather than one per card. A browser holding a stale copy
            # of the plan disagrees about every card it carries, and a hundred rows of the
            # same fact is not a better signal than one.
            frappe.log_error(
                title="Transportation Shipment Direction Mismatch",
                message=(
                    "Left as they are - the plan still places these cards, so what needs "
                    "looking at is the direction flag, not the status:\n\n"
                    + "\n".join(mismatched)
                ),
            )

    for name in assigned:
        if frappe.db.get_value("Transportation Shipment", name, "status") != "Assigned":
            frappe.db.set_value("Transportation Shipment", name, "status", "Assigned")

    # Revert only shipments this plan dropped — never touch shipments that are
    # placed in a different Route Plan.
    from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
        unmerge_trip_shipment,
    )

    # A card the plan still places is never reverted, whatever its direction flag says.
    # `status` answers "is this shipment on a plan", and a direction mismatch does not
    # change that answer - it means the two sides disagree about which leg, which is a
    # flag to fix rather than a card to send back to the pool. Reverting one that is
    # still on a lane marked it Unassigned while its block sat there, and Generate
    # Shipments deletes Unassigned shift-generated cards whose demand has moved on - so a
    # browser left open across a data change could get a placed card deleted.
    still_placed = set(placed_dirs_by_shipment)

    for name in (previously_linked or set()):
        if not name or name in assigned or name in still_placed:
            continue
        if frappe.db.exists("Transportation Shipment", name):
            frappe.db.set_value("Transportation Shipment", name, "status", "Unassigned")
            # A card returning to the pool takes its own direction back with it. Being
            # merged is a property of the block it was in, not of the journey the shipment
            # was generated for (WI-002071).
            unmerge_trip_shipment(name)

    # A card still on the plan but no longer placed as part of a merged trip is also no
    # longer merged - the operator can break a merge by dragging one stop out without
    # removing the other.
    for name in assigned:
        if "MIXED" not in placed_dirs_by_shipment.get(name, set()):
            unmerge_trip_shipment(name)


def _link_shipment_on_manifest_rows(manifest_doc, v_rows, card_emp_map):
    """Set transportation_shipment on manifest detail rows for shipment blocks.

    Builds an employee -> shipment map from this vehicle's shipment-backed
    assignment rows and stamps it onto the matching manifest detail rows.
    Returns True if any row was changed. Only ever sets an extra reference
    field, so it never disturbs the reliever/attendance sync.
    """
    emp_to_ship = {}
    for row in v_rows:
        if not row.transportation_shipment:
            continue
        for emp in card_emp_map.get(row.card_id, []):
            emp_id = emp.get("id")
            if emp_id:
                emp_to_ship[emp_id] = row.transportation_shipment

    if not emp_to_ship:
        return False

    changed = False
    for detail in manifest_doc.transportation_manifest_details:
        shipment = emp_to_ship.get(detail.employee)
        if shipment and detail.transportation_shipment != shipment:
            detail.transportation_shipment = shipment
            changed = True
    return changed


@frappe.whitelist()
def save_assignments(plan_name: str, swim_items: str, assigned_cards: str,
                     leg_timings: str = None):
    """Save route planner swim items into a Route Plan DocType.

    ``leg_timings`` carries the minutes for the legs no card is filed against - the drive
    out of each accommodation - keyed by trip group and then by camp. They have no block
    on the lane to ride in on, so they are sent alongside the items and land on the camp
    rows _stamp_leg_details writes.
    """
    if not _route_plan_exists():
        frappe.throw(_("Route Plan DocType not found. Please run 'bench migrate' on this site first."))

    import json
    items = json.loads(swim_items)
    cards = json.loads(assigned_cards)
    legs = json.loads(leg_timings) if isinstance(leg_timings, str) else (leg_timings or {})

    doc = frappe.get_doc("Route Plan", plan_name)
    doc.check_permission("write")

    # Remember shipments this plan previously carried so we can revert only the
    # ones this plan drops (never touching shipments placed in another plan).
    previously_linked = {
        row.transportation_shipment for row in doc.assignments if row.transportation_shipment
    }

    # Clear existing assignments and rebuild
    doc.assignments = []
    directions = _shipment_direction_flags(items)
    for item in _with_stop_indexes(items):
        shipment = _shipment_from_card_id(item.get("cardId", ""))
        doc.append("assignments", {
            "card_id":                 item.get("cardId", ""),
            "transportation_shipment": shipment,
            "vehicle":                 item.get("vehicleId", ""),
            "direction":               _assignment_direction(item, directions.get(shipment)),
            "stop_index":              item.get("stopIndex", 0),
            "trip_group":              item.get("tripId", ""),
            "trip_name":               item.get("tripName", ""),
            "headcount":               item.get("headcount", 0),
            "start_time":              item.get("start", ""),
            "end_time":                item.get("end", ""),
            "site":                    item.get("_site", ""),
            "shift":                   item.get("_shift", ""),
            "accommodation":           item.get("_accommodation", ""),
            "stop_location":           item.get("_stopLocation", ""),
            "transit_minutes":         item.get("transitMinutes") or 0,
            "buffer_minutes":          item.get("bufferMinutes") or 0,
        })

    _stamp_leg_details(doc, legs)
    doc.save(ignore_permissions=False)

    # Keep persisted Transportation Shipment records in sync with the canvas:
    # any shipment now placed on a vehicle becomes Assigned; any shipment this
    # plan dropped back into the pool reverts to Unassigned.
    _sync_shipment_statuses(items, previously_linked)

    return {
        "status": "ok",
        "plan_name": doc.name,
        "saved_at": str(doc.last_modified_at or frappe.utils.now()),
        "assignment_count": len(doc.assignments)
    }


@frappe.whitelist()
def load_assignments(plan_name: str = ""):
    """Load saved route planner swim items from a Route Plan.
    If plan_name is empty, loads the currently Active plan.
    """
    if not _route_plan_exists():
        return {"status": "empty", "message": _("Route Plan DocType not migrated yet.")}

    if not plan_name:
        # Prioritize the plan marked as default; fall back to Active if no default
        plan_name = frappe.db.get_value("Route Plan", {"is_default": 1}, "name")
        if not plan_name:
            plan_name = frappe.db.get_value("Route Plan", {"status": "Active"}, "name")

    if not plan_name:
        return {"status": "empty"}

    doc = frappe.get_doc("Route Plan", plan_name)
    doc.check_permission("read")

    swim_items = []
    assigned_card_ids = set()
    # The minutes of the legs no card is filed against, keyed by the run and the camp
    # they leave. Without them a re-opened Trip Builder showed the camp leg back on a
    # default nobody typed, and every stop after it moved with it.
    leg_timings = {}

    for row in doc.assignments:
        if cint(row.is_camp_leg):
            place = row.origin_location or row.stop_location
            if place:
                leg_timings.setdefault(row.trip_group or camp_leg_group(row.card_id), {})[place] = {
                    "transit_minutes": row.transit_minutes or 0,
                    "buffer_minutes": row.buffer_minutes or 0,
                }
            continue

        swim_items.append({
            "id":        f"{row.card_id}_{row.direction}_{row.name}",
            "cardId":    row.card_id,
            "vehicleId": row.vehicle,
            "direction": row.direction,
            "start":     row.start_time,
            "end":       row.end_time,
            "headcount": row.headcount or 0,
            "conflict":  False,
            "tripId":    row.trip_group or None,
            "tripName":  row.trip_name or None,
            "stopIndex": row.stop_index or 0,
            "totalStops": 0,  # recalculated client-side
            # Per-leg minutes as typed in the Merge Trip modal. Round-tripped rather
            # than re-derived from the timestamps: the block position is a rendering of
            # these numbers, and reading it backwards loses the operator's intent
            # (a 0-minute buffer and a 0-minute gap are not the same statement).
            "transitMinutes": row.transit_minutes or 0,
            "bufferMinutes": row.buffer_minutes or 0,
            # Saved metadata for detail panel fallback
            "_site":          row.site or "",
            "_shift":         row.shift or "",
            "_accommodation": row.accommodation or "",
            "_stopLocation":  row.stop_location or "",
        })
        assigned_card_ids.add(row.card_id)

    # Recalculate totalStops per trip group
    trip_counts = {}
    for item in swim_items:
        if item["tripId"]:
            trip_counts[item["tripId"]] = trip_counts.get(item["tripId"], 0) + 1
    for item in swim_items:
        if item["tripId"] and item["tripId"] in trip_counts:
            item["totalStops"] = trip_counts[item["tripId"]]

    return {
        "status": "ok",
        "leg_timings": leg_timings,
        "plan_name": doc.name,
        "plan_title": doc.title,
        "plan_status": doc.status,
        "effective_from": str(doc.effective_from) if doc.effective_from else None,
        "effective_until": str(doc.effective_until) if doc.effective_until else None,
        "is_default": doc.is_default,
        "swim_items": swim_items,
        "assigned_cards": list(assigned_card_ids),
        "saved_by": doc.last_modified_by_user,
        "saved_at": str(doc.last_modified_at) if doc.last_modified_at else None
    }


@frappe.whitelist()
def get_manifest_data_for_plan(plan_name: str):
	"""Build manifest ROUTE_DATA from a saved Route Plan.

	This is the server-side equivalent of the client-side buildManifestData().
	It reconstructs the manifest JSON from the plan's saved assignments and
	live employee/vehicle/shift data so that the Transportation Manifest page
	can render without depending on in-memory state.
	"""
	if not _route_plan_exists():
		frappe.throw(_("Route Plan DocType not found. Please run 'bench migrate' on this site first."))

	doc = frappe.get_doc("Route Plan", plan_name)
	doc.check_permission("read")

	# A camp leg describes a stop the bus makes; no card is filed against it and it
	# carries no roster, so the manifest is compiled from the rows that stand for one.
	rows = card_rows(doc.assignments)
	if not rows:
		return {"status": "empty", "message": _("This plan has no assignments.")}

	slug = lambda s: (s or "").replace(" ", "-").replace("_", "-")

	# ── Collect unique references from assignments ──
	vehicle_ids = list({row.vehicle for row in rows if row.vehicle})
	shift_names = list({row.shift for row in rows if row.shift})

	# ── Batch-fetch vehicle metadata ──
	vehicle_map = {}
	if vehicle_ids:
		for v in frappe.get_all("Vehicle",
			filters={"name": ["in", vehicle_ids]},
			fields=["name", "license_plate", "location", "seats",
					"one_fm_vehicle_type", "make", "model", "employee"]
		):
			vehicle_map[v.name] = v

	# Batch-fetch driver names
	emp_ids_for_drivers = [v.employee for v in vehicle_map.values() if v.employee]
	driver_map = {}
	if emp_ids_for_drivers:
		for row in frappe.get_all("Employee",
			filters={"name": ["in", emp_ids_for_drivers]},
			fields=["name", "employee_name"]
		):
			driver_map[row.name] = row.employee_name

	# Batch-fetch accommodation labels for vehicle locations
	veh_locations = list({v.location for v in vehicle_map.values() if v.location})
	veh_acc_map = {}
	if veh_locations:
		for row in frappe.get_all("Accommodation",
			filters={"transport_stop_location": ["in", veh_locations]},
			fields=["transport_stop_location", "accommodation"]
		):
			veh_acc_map[row.transport_stop_location] = row.accommodation

	MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

	# ── Batch-fetch shift docs ──
	shift_doc_map = {}
	if shift_names:
		for s in frappe.get_all("Operations Shift",
			filters={"name": ["in", shift_names]},
			fields=["name", "site", "start_time", "end_time"]
		):
			shift_doc_map[s.name] = s

	# ── Batch-fetch site locations ──
	all_sites = list({s.site for s in shift_doc_map.values() if s.site})
	site_location_map = {}
	if all_sites:
		for row in frappe.get_all("Operations Site",
			filters={"name": ["in", all_sites]},
			fields=["name", "site_location"]
		):
			site_location_map[row.name] = row.site_location or row.name

	# ── Fetch shipment cards for employee data ──
	# We need the live employee lists from get_route_planner_data.
	# Build a card_id -> employee list map from shipment cards.
	try:
		planner_data = get_route_planner_data()
		if planner_data.get("status") != "ok":
			planner_data = {"shipment_cards": [], "vehicles": []}
	except Exception:
		planner_data = {"shipment_cards": [], "vehicles": []}

	card_emp_map = {}
	card_return_emp_map = {}
	card_headcount_map = {}
	for card in planner_data.get("shipment_cards", []):
		card_emp_map[card["id"]] = card.get("employees", [])
		card_return_emp_map[card["id"]] = card.get("return_employees", [])
		card_headcount_map[card["id"]] = card.get("headcount", 0)

	# Supplement rosters for shipment-backed assignment rows. Once a shipment is
	# Assigned it no longer surfaces as an Unassigned pool card above, so pull its
	# employee list straight from the shipment document instead.
	shipment_by_card = {
		row.card_id: row.transportation_shipment
		for row in rows
		if row.transportation_shipment and row.card_id not in card_emp_map
	}
	if shipment_by_card:
		ship_names = list({v for v in shipment_by_card.values() if v})
		emps_by_ship = {}
		for r in frappe.get_all(
			"Transportation Shipment Employee",
			filters={"parent": ["in", ship_names], "parenttype": "Transportation Shipment"},
			fields=["parent", "employee_id", "employee_name", "cell_number"],
			order_by="idx asc",
		):
			emps_by_ship.setdefault(r.parent, []).append(
				{"id": r.employee_id, "name": r.employee_name or r.employee_id, "mobile": r.cell_number or ""}
			)
		for card_id, ship_name in shipment_by_card.items():
			emps = emps_by_ship.get(ship_name, [])
			card_emp_map[card_id] = emps
			card_return_emp_map[card_id] = []
			card_headcount_map[card_id] = len(emps)

	# ── Build manifest data structure ──
	shipments = []
	vehicles_list = []
	routes = []
	ship_emp = {}
	ship_return_emp = {}
	ship_site = {}
	ship_shift = {}
	v_meta = {}
	c_map = {}  # dirKey -> { lbl, idx }
	si = 0

	# Lazily sync Transportation Manifest documents for each vehicle on today's date
	schedule_date_str = frappe.utils.today()
	assigned_vehicles = list({row.vehicle for row in rows if row.vehicle})
	
	manifests = {}

	for v_id in assigned_vehicles:
		manifest_name = frappe.db.get_value(
			"Transportation Manifest",
			{"vehicle_no": v_id, "schedule_date": schedule_date_str},
			"name"
		)
		if manifest_name:
			manifest_doc = frappe.get_doc("Transportation Manifest", manifest_name)
		else:
			if not frappe.has_permission("Transportation Manifest", "create"):
				continue
			manifest_doc = frappe.new_doc("Transportation Manifest")
			manifest_doc.vehicle_no = v_id
			manifest_doc.schedule_date = schedule_date_str

		# Always sync rows — handles both new and existing manifests
		v_rows = [row for row in rows if row.vehicle == v_id]
		rows_changed = sync_manifest_details(manifest_doc, v_rows, card_emp_map, card_return_emp_map)

		# The manifest header inherits the run's direction and, for a merged run, its
		# shared group key (WI-002072). Read from the assignment rows rather than passed
		# in, because those rows are what the vehicle is actually scheduled to do today.
		if _inherit_trip_identity(manifest_doc, v_rows):
			rows_changed = True

		# Stamp the source shipment onto the compiled manifest detail rows so the
		# vehicle's manifest array references the Transportation Shipment record.
		if _link_shipment_on_manifest_rows(manifest_doc, v_rows, card_emp_map):
			rows_changed = True

		# Recompute per-camp stop numbering in memory so existing manifests pick up
		# the current sequencing rule (per unique camp, incl. Direct) even when their
		# rows are otherwise unchanged — the manifest page's per-camp banners + lock
		# depend on it (MA2-11). Persist if the numbers actually shifted.
		_old_seqs = [(r.name, r.stop_sequence) for r in manifest_doc.transportation_manifest_details]
		manifest_doc.populate_stop_sequence_and_pickup_accommodation()
		if _old_seqs != [(r.name, r.stop_sequence) for r in manifest_doc.transportation_manifest_details]:
			rows_changed = True

		if manifest_doc.is_new():
			manifest_doc.insert()
		elif rows_changed:
			manifest_doc.check_permission("write")
			manifest_doc.save()

		manifests[v_id] = manifest_doc

	# Resolve Accommodation display labels once (collapsing Mahboula sub-camps),
	# so the manifest page can group boarding staff camp-by-camp (MA2-11).
	acc_label_cache = {}

	def _acc_label(acc):
		if not acc:
			return None
		if acc not in acc_label_cache:
			lbl = frappe.db.get_value("Accommodation", acc, "accommodation") or acc
			acc_label_cache[acc] = "Mahboula Camp" if lbl in MAHBOULA_LABELS else lbl
		return acc_label_cache[acc]

	def enrich_employees(emp_list, vehicle_id, stop_location, trip_id, is_return):
		manifest_doc = manifests.get(vehicle_id)
		if not manifest_doc:
			return emp_list
			
		enriched = []
		action = "Dropping Off" if is_return else "Boarding"
		stop_location_normalized = stop_location or ""
		direction = "RETURN" if is_return else "OUTBOUND"
		stop_id_val = f"{stop_location_normalized}|{direction}"
		
		for emp in emp_list:
			emp_id = emp.get("id")
			matching_row = None
			# Primary match: compound key using stop_id
			for row in manifest_doc.transportation_manifest_details:
				if (row.employee == emp_id and 
					(row.stop_id or "") == stop_id_val and 
					(row.trip_id or "") == (trip_id or "") and 
					row.employee_action == action):
					matching_row = row
					break
			# Fallback: match by stop_name for rows created before stop_id was added
			if not matching_row:
				for row in manifest_doc.transportation_manifest_details:
					if (row.employee == emp_id and 
						(row.stop_name or "") == stop_location_normalized and 
						(row.trip_id or "") == (trip_id or "") and 
						row.employee_action == action):
						matching_row = row
						break
			
			if not matching_row:
				for row in manifest_doc.transportation_manifest_details:
					if row.employee == emp_id:
						matching_row = row
						break
						
			emp_copy = dict(emp)
			# Manifest link is stamped regardless of match so the page can wire the
			# per-camp attendance-check trigger/lock to the right manifest (MA2-11).
			emp_copy["manifest"] = manifest_doc.name if not manifest_doc.is_new() else None
			if matching_row:
				emp_copy["row_id"] = matching_row.name
				emp_copy["attendance_status"] = matching_row.attendance_status
				emp_copy["qoa_status"] = matching_row.qoa_status
				emp_copy["qoa_reason"] = matching_row.qoa_reason
				emp_copy["requires_reliever"] = matching_row.requires_reliever
				emp_copy["reliever_employee"] = matching_row.reliever_employee
				# Pickup camp + stop sequence drive the DEPART camp banners and the
				# strictly-sequential unlock (MA2-11).
				emp_copy["pickup_accommodation"] = matching_row.pickup_accommodation
				emp_copy["pickup_camp_label"] = _acc_label(matching_row.pickup_accommodation)
				emp_copy["stop_sequence"] = matching_row.stop_sequence or 1
				emp_copy["operations_shift"] = matching_row.operations_shift
				emp_copy["operations_site"] = matching_row.operations_site
				emp_copy["operations_role"] = matching_row.operations_role
				emp_copy["project"] = matching_row.project
				emp_copy["start_time"] = str(matching_row.start_time) if matching_row.start_time else None
				emp_copy["end_time"] = str(matching_row.end_time) if matching_row.end_time else None
				
				if matching_row.reliever_employee:
					rel_name = frappe.db.get_value("Employee", matching_row.reliever_employee, "employee_name") or matching_row.reliever_employee
					rel_mobile = frappe.db.get_value("Employee", matching_row.reliever_employee, "cell_number") or ""
					emp_copy["replacement"] = {
						"id": matching_row.reliever_employee,
						"name": rel_name,
						"mobile": rel_mobile
					}
			else:
				emp_copy["row_id"] = ""
				
			enriched.append(emp_copy)
		return enriched

	# Which way each card's own riders travel. A merged card is labelled MIXED, so the
	# label can no longer say whether its riders board at the stop or leave there - and
	# the manifest page decides drop-off vs pick-up from exactly that (WI-002074).
	ship_own_dir = {}
	_own_dir_by_shipment = {}
	_ship_names = [r.transportation_shipment for r in rows if r.transportation_shipment]
	if _ship_names:
		for _r in frappe.get_all(
			"Transportation Shipment",
			filters={"name": ["in", list(set(_ship_names))]},
			fields=["name", "trip_direction", "pre_merge_trip_direction"],
		):
			_own_dir_by_shipment[_r.name] = _card_direction(
				_r.trip_direction, _r.pre_merge_trip_direction
			)

	# Process assignments to build shipments
	for row in rows:
		dir_key = f"{row.card_id}_{row.direction}"
		if dir_key in c_map:
			continue  # Already created shipment for this card+direction

		lbl = f"{slug(row.accommodation)}_{si}_{slug(row.stop_location)}_{row.direction}"
		idx = si
		si += 1

		shipments.append({"label": lbl, "pickups": [{}], "deliveries": [{}]})

		# Map employees
		if row.direction == "RETURN":
			ret_emps = card_return_emp_map.get(row.card_id, [])
			ship_emp[lbl] = enrich_employees(ret_emps, row.vehicle, row.stop_location or "", row.trip_group, True) if ret_emps else []
		else:
			emps = card_emp_map.get(row.card_id, [])
			ship_emp[lbl] = enrich_employees(emps, row.vehicle, row.stop_location or "", row.trip_group, False) if emps else []

		ret_emps = card_return_emp_map.get(row.card_id, [])
		ship_return_emp[lbl] = enrich_employees(ret_emps, row.vehicle, row.stop_location or "", row.trip_group, True) if ret_emps else []

		# Site location
		if row.shift and row.shift in shift_doc_map:
			shift_site = shift_doc_map[row.shift].site
			ship_site[lbl] = site_location_map.get(shift_site, row.stop_location or "")
		else:
			ship_site[lbl] = row.stop_location or ""

		ship_shift[lbl] = row.shift or ""
		ship_own_dir[lbl] = _own_dir_by_shipment.get(
			row.transportation_shipment
		) or _normalize_direction(row.direction)
		c_map[dir_key] = {"lbl": lbl, "idx": idx}

	# ── Build vehicles and routes ──
	# Group assignments by vehicle, preserving trip order
	vehicle_order = []
	vehicle_items = {}  # vehicle_id -> [rows]
	for row in rows:
		if row.vehicle not in vehicle_items:
			vehicle_items[row.vehicle] = []
			vehicle_order.append(row.vehicle)
		vehicle_items[row.vehicle].append(row)

	for vi, vid in enumerate(vehicle_order):
		v_doc = vehicle_map.get(vid, {})
		v_label = vid
		driver_name = driver_map.get(v_doc.get("employee"), "\u2014") if v_doc.get("employee") else "\u2014"
		acc_label = veh_acc_map.get(v_doc.get("location"), v_doc.get("location", ""))
		if acc_label in MAHBOULA_LABELS:
			acc_label = "Mahboula Camp"

		vehicles_list.append({"label": v_label, "startLocation": None})
		_mf = manifests.get(vid)
		v_meta[v_label] = {
			"accommodation": acc_label,
			"driver": driver_name,
			"seats": v_doc.get("seats") or 0,
			"location": v_doc.get("location", ""),
			"license_plate": v_doc.get("license_plate", ""),
			"make": v_doc.get("make", ""),
			# WI-001766: the manifest identifies the bus as "<plate>, <model>", so the
			# model travels with the plate rather than being looked up on site.
			"model": v_doc.get("model", ""),
			"type": v_doc.get("one_fm_vehicle_type", ""),
			# Attendance-check lock state for this vehicle's manifest (MA2-11):
			# active_stop_sequence drives which pickup camp is currently unlocked.
			"manifest": _mf.name if (_mf and not _mf.is_new()) else None,
			"active_stop_sequence": int(_mf.active_stop_sequence or 0) if _mf else 0,
			# WI-002074: the manifest page badges a merged run and reads its whole
			# itinerary differently. Without these it had no way to tell, so the MIXED
			# badge never rendered and the merged-run attendance rule never applied.
			"trip_direction": (_mf.trip_direction or "") if _mf else "",
			"trip_group": (_mf.trip_group or "") if _mf else "",
		}

		# Sort items: trip stops by stopIndex, solo by start_time
		v_rows = vehicle_items[vid]
		v_rows.sort(key=lambda r: (
			r.trip_group or "",
			r.stop_index or 0,
			r.start_time or ""
		))

		visits = []
		trans = [{"travelDuration": "0s", "waitDuration": "0s", "travelDistanceMeters": 0}]

		for idx_r, row in enumerate(v_rows):
			dir_key = f"{row.card_id}_{row.direction}"
			info = c_map.get(dir_key)
			if not info:
				continue

			s_idx = info["idx"]
			hc = row.headcount or 0
			i_s = row.start_time or ""
			i_e = row.end_time or ""

			# Calculate duration in seconds. start_time/end_time carry the multi-day
			# lock lifespan in their DATE part, so we take only the time-of-day
			# difference — the run itself is a single-day trip (a 6-day lock is still
			# a ~1h daily ride); otherwise the manifest would report a multi-day
			# travel duration.
			try:
				from datetime import datetime as dt_cls
				dt_start = dt_cls.fromisoformat(i_s.replace("Z", "+00:00")).replace(tzinfo=None)
				dt_end = dt_cls.fromisoformat(i_e.replace("Z", "+00:00")).replace(tzinfo=None)
				d_sec = int((dt_end - dt_start).total_seconds()) % 86400
			except Exception:
				d_sec = 0

			visits.append({
				"shipmentIndex": s_idx, "isPickup": True, "startTime": i_s,
				"loadDemands": {"seats": {"amount": str(hc)}},
				"tripId": row.trip_group or None,
				"tripName": row.trip_name or None,
				"stopIndex": row.stop_index or 0,
				"transitMinutes": row.transit_minutes or 0,
				"bufferMinutes": row.buffer_minutes or 0
			})
			travel_sec = (row.transit_minutes or 0) * 60 or d_sec
			trans.append({
				"travelDuration": f"{travel_sec}s",
				"waitDuration": f"{(row.buffer_minutes or 0) * 60}s",
				"travelDistanceMeters": travel_sec * 10
			})
			visits.append({
				"shipmentIndex": s_idx, "isPickup": False, "startTime": i_e,
				"loadDemands": {"seats": {"amount": str(-hc)}},
				"tripId": row.trip_group or None,
				"tripName": row.trip_name or None,
				"stopIndex": row.stop_index or 0,
				"transitMinutes": row.transit_minutes or 0,
				"bufferMinutes": row.buffer_minutes or 0
			})

			# Gap to next item
			if idx_r < len(v_rows) - 1:
				nxt = v_rows[idx_r + 1]
				try:
					nxt_start = dt_cls.fromisoformat((nxt.start_time or "").replace("Z", "+00:00")).replace(tzinfo=None)
					# Time-of-day gap only (ignore the multi-day lifespan date part).
					gap = int((nxt_start - dt_end).total_seconds()) % 86400
				except Exception:
					gap = 0
			else:
				gap = 0
			trans.append({
				"travelDuration": f"{gap}s", "waitDuration": "0s",
				"travelDistanceMeters": gap * 8
			})

		if not visits:
			continue

		# Route start/end times
		r_s = v_rows[0].start_time or ""
		r_e = v_rows[-1].end_time or ""
		try:
			# Daily route span — time-of-day only, so a multi-day lock does not
			# balloon the reported route/trip duration into days.
			tot_ms = (dt_cls.fromisoformat(r_e.replace("Z", "+00:00")).replace(tzinfo=None)
					  - dt_cls.fromisoformat(r_s.replace("Z", "+00:00")).replace(tzinfo=None)).total_seconds() % 86400
			trip_ms = sum(
				int((dt_cls.fromisoformat((r.end_time or "").replace("Z", "+00:00")).replace(tzinfo=None)
						- dt_cls.fromisoformat((r.start_time or "").replace("Z", "+00:00")).replace(tzinfo=None)).total_seconds()) % 86400
				for r in v_rows
			)
		except Exception:
			tot_ms = 0
			trip_ms = 0

		MAX_DAY_SEC = 86400
		total_sec = min(int(tot_ms), MAX_DAY_SEC)
		trip_sec = min(int(trip_ms), MAX_DAY_SEC)

		routes.append({
			"vehicleIndex": vi, "vehicleLabel": v_label,
			"vehicleStartTime": r_s, "vehicleEndTime": r_e,
			"visits": visits, "transitions": trans,
			"metrics": {
				"travelDistanceMeters": 0,
				"totalDuration": f"{total_sec}s",
				"travelDuration": f"{trip_sec}s"
			}
		})

	return {
		"status": "ok",
		"plan_name": doc.name,
		"plan_title": doc.title,
		"route_data": {
			"request": {
				"model": {
					"shipments": shipments,
					"vehicles": vehicles_list,
				}
			},
			"response": {
				"routes": routes,
				"skippedShipments": [],
				"metrics": {"totalCost": 0}
			},
			"shipmentEmployees": ship_emp,
			"shipmentReturnEmployees": ship_return_emp,
			"shipmentSiteLocations": ship_site,
			"shipmentShiftNames": ship_shift,
			"shipmentOwnDirections": ship_own_dir,
			"vehicleMeta": v_meta
		}
	}


@frappe.whitelist()
def create_route_plan(title: str, effective_from: str, effective_until: str = "", is_default: int = 0):
    """Create a new Route Plan and return its name."""
    if not _route_plan_exists():
        frappe.throw(_("Route Plan DocType not found. Please run 'bench migrate' on this site first."))

    doc = frappe.new_doc("Route Plan")
    doc.title = title
    doc.effective_from = effective_from
    doc.effective_until = effective_until or None
    doc.is_default = cint(is_default)
    doc.status = "Draft"
    doc.insert()
    return {
        "status": "ok",
        "plan_name": doc.name,
        "plan_title": doc.title
    }


@frappe.whitelist()
def update_route_plan_status(plan_name: str, new_status: str):
    """Update the status of a Route Plan (Draft / Active / Expired).
    When activating a plan, deactivate any other currently Active plan.
    """
    if not _route_plan_exists():
        frappe.throw(_("Route Plan DocType not found. Please run 'bench migrate' on this site first."))

    if new_status not in ("Draft", "Active", "Expired"):
        frappe.throw(_("Invalid status: {0}. Must be Draft, Active, or Expired.").format(new_status))

    doc = frappe.get_doc("Route Plan", plan_name)
    doc.check_permission("write")

    # Deactivate any currently Active plan before activating this one
    if new_status == "Active":
        active_plans = frappe.get_list("Route Plan",
            filters={"status": "Active", "name": ["!=", plan_name]},
            fields=["name"]
        )
        for ap in active_plans:
            frappe.db.set_value("Route Plan", ap.name, "status", "Draft")

    doc.db_set("status", new_status)
    frappe.db.commit()

    return {
        "status": "ok",
        "plan_name": doc.name,
        "new_status": new_status
    }
@frappe.whitelist()
def get_available_rambo_relievers(shift_name: str = None, date: str = None):
    """
    Fetch available Rambo relievers for a specific date.
    Returns employees with custom_is_rambo_reliever = 1 and status = 'Active',
    enriched with their current day's Operations Shift details (if scheduled).

    Dropdown display format: [Name] - [Shift] - [Start] to [End]
    Falls back to [Name] ([Designation]) if no shift is assigned.
    """
    if not date:
        date = frappe.utils.today()

    from frappe.query_builder import DocType

    Employee = DocType("Employee")
    rambos = (
        frappe.qb.from_(Employee)
        .select(
            Employee.name,
            Employee.employee_name,
            Employee.designation,
            Employee.cell_number,
            Employee.shift,
        )
        .where(Employee.status == "Active")
        .where(Employee.custom_is_rambo_reliever == 1)
        .orderby(Employee.employee_name)
    ).run(as_dict=True)

    if not rambos:
        return []

    rambo_ids = [r.name for r in rambos]

    # Fetch Employee Schedule for these employees on the given date.
    # Filter to roster_type='Basic' to avoid ambiguity with Over-Time entries
    # (consistent with one_fm/api/tasks.py and default_shift_checker.py).
    EmployeeSchedule = DocType("Employee Schedule")
    schedules = (
        frappe.qb.from_(EmployeeSchedule)
        .select(
            EmployeeSchedule.employee,
            EmployeeSchedule.shift,
        )
        .where(EmployeeSchedule.employee.isin(rambo_ids))
        .where(EmployeeSchedule.date == date)
        .where(EmployeeSchedule.employee_availability == "Working")
        .where(EmployeeSchedule.roster_type == "Basic")
    ).run(as_dict=True)

    # Map employee → today's scheduled shift
    emp_schedule_map = {}
    for s in schedules:
        if s.employee not in emp_schedule_map:
            emp_schedule_map[s.employee] = s.shift

    # Collect all shift names we need details for (from schedule + fallback default)
    all_shift_names = set()
    for r in rambos:
        scheduled_shift = emp_schedule_map.get(r.name)
        if scheduled_shift:
            all_shift_names.add(scheduled_shift)
        elif r.shift:
            all_shift_names.add(r.shift)

    # Batch-fetch Operations Shift details
    shift_detail_map = {}
    if all_shift_names:
        OperationsShift = DocType("Operations Shift")
        shift_details = (
            frappe.qb.from_(OperationsShift)
            .select(
                OperationsShift.name,
                OperationsShift.start_time,
                OperationsShift.end_time,
            )
            .where(OperationsShift.name.isin(list(all_shift_names)))
        ).run(as_dict=True)
        shift_detail_map = {s.name: s for s in shift_details}

    # Build response
    result = []
    for r in rambos:
        # Determine which shift to display: Employee Schedule (today) → fallback to default
        effective_shift = emp_schedule_map.get(r.name) or r.shift
        shift_doc = shift_detail_map.get(effective_shift) if effective_shift else None

        result.append({
            "name": r.name,
            "employee_name": r.employee_name,
            "designation": r.designation or "",
            "mobile": r.cell_number or "",
            "shift_name": effective_shift if shift_doc else None,
            "shift_start_time": frappe.utils.get_time(shift_doc.start_time).strftime("%H:%M") if shift_doc else None,
            "shift_end_time": frappe.utils.get_time(shift_doc.end_time).strftime("%H:%M") if shift_doc else None,
        })

    return result


@frappe.whitelist()
def process_rambo_replacement(original_employee: str, replacement_employee: str, shift_name: str, site: str):
    """
    Processes the swap by sending an email notification.
    The UI will update its own DOM/State dynamically.
    """
    orig_emp = frappe.db.get_value("Employee", original_employee, "employee_name") or original_employee
    new_emp = frappe.db.get_value("Employee", replacement_employee, "employee_name") or replacement_employee
    
    # Send Email Notification
    recipients = []
    
    # Find operations supervisor for the shift/site
    if shift_name:
        supervisor = frappe.db.get_value("Operations Shift", shift_name, "supervisor")
        if supervisor:
            user_id = frappe.db.get_value("Employee", supervisor, "user_id")
            if user_id:
                user_email = frappe.db.get_value("User", user_id, "email")
                if user_email:
                    recipients.append(user_email)
    
    if recipients:
        subject = f"Rambo Reliever Swap: {orig_emp} replaced by {new_emp}"
        message = f"""
        <p>A Rambo Reliever replacement has been processed from the Route Planner Manifest.</p>
        <ul>
            <li><b>Site:</b> {site}</li>
            <li><b>Shift:</b> {shift_name}</li>
            <li><b>Original Employee (Absent/Fail):</b> {orig_emp}</li>
            <li><b>Rambo Reliever (Replacement):</b> {new_emp}</li>
        </ul>
        <p>Please note that this is an automated message.</p>
        """
        
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                now=True
            )
            return {
                "status": "success",
                "notified": True,
                "message": "Replacement processed and supervisor notified."
            }
        except Exception as e:
            frappe.log_error(f"Error sending Rambo Reliever notification: {str(e)}", "Rambo Reliever Notification")
            return {
                "status": "success",
                "notified": False,
                "message": "Replacement processed, but notification email failed."
            }

    return {
        "status": "success",
        "notified": False,
        "message": "Replacement processed. No supervisor found for this shift to notify."
    }


def _shipment_direction_flags(items) -> dict:
    """{shipment: OUTBOUND|RETURN|MIXED} for every card being saved (WI-002077).

    Read in one query rather than per row: a full month's canvas is hundreds of items.
    """
    names = {
        _shipment_from_card_id(item.get("cardId", ""))
        for item in items
        if _shipment_from_card_id(item.get("cardId", ""))
    }
    if not names:
        return {}

    return {
        row.name: _normalize_direction(row.trip_direction)
        for row in frappe.get_all(
            "Transportation Shipment",
            filters={"name": ["in", list(names)]},
            fields=["name", "trip_direction"],
        )
    }


def _assignment_direction(item, shipment_direction: str) -> str:
    """The direction a row is written with (WI-002077).

    Taken from the card's own Transportation Shipment rather than from whatever the
    canvas sent, which is what "auto-fetched from the Transportation Shipment card"
    asks for. The two sides use different vocabularies - the shipment says Outward,
    the assignment says OUTBOUND - so this is a mapping and not a fetch_from; declaring
    one would write "Outward" into a Select that does not offer it.

    A merged card carries MIXED, so every row of one merged trip agrees on it without
    the canvas having to say so.

    Falls back to the canvas value when the shipment cannot be read - a row placed by
    hand with no shipment link still has a direction worth keeping.
    """
    if shipment_direction:
        return shipment_direction

    return _normalize_direction(item.get("direction", ""))


def _with_stop_indexes(items):
    """Number the stops of each merged trip 1, 2, 3... in chronological order (WI-002077).

    A merged trip's rows have to carry an explicit position, because the manifest and the
    per-leg capacity walk both read the run in stop order and neither can infer it from
    table order. The canvas sends stopIndex for the multi-stop cards it already sequences;
    a trip merged by dropping one card onto another has no index yet, so the order is
    derived from the start times the modal produced.

    Only rows sharing a trip_group are numbered. A standalone card is its own trip and its
    index is left exactly as the canvas sent it.
    """
    grouped = {}
    for item in items:
        group = item.get("tripId")
        if group:
            grouped.setdefault(group, []).append(item)

    for members in grouped.values():
        if len(members) < 2:
            continue
        # Sorted on the start the modal computed; a member with no start sorts last so it
        # cannot silently take the head of the run.
        ordered = sorted(members, key=lambda i: (not i.get("start"), i.get("start") or "", i.get("cardId", "")))
        for position, member in enumerate(ordered, start=1):
            member["stopIndex"] = position

    return items


def _inherit_trip_identity(manifest_doc, assignment_rows) -> bool:
    """Copy the run's direction and trip group onto the manifest header (WI-002072).

    A vehicle running a merged trip produces a Mixed manifest carrying the same
    trip_group as the plan, so a manifest can be traced back to the schedule block it
    came from. Only a merged run has a group key; a plain outbound or return run has
    nothing to share and leaves it empty.

    Returns whether anything changed, so the caller only saves when it has to.
    """
    directions = {(row.direction or "").upper() for row in assignment_rows if row.direction}
    if not directions:
        return False

    if "MIXED" in directions:
        trip_direction = "Mixed"
        # Every row of one merged trip carries the same key (WI-002077); taking the
        # first non-empty one is enough and does not depend on row order.
        trip_group = next(
            (row.trip_group for row in assignment_rows
             if (row.direction or "").upper() == "MIXED" and row.trip_group),
            None,
        )
    else:
        trip_direction = "Return" if directions == {"RETURN"} else "Outward"
        trip_group = None

    changed = False
    if manifest_doc.get("trip_direction") != trip_direction:
        manifest_doc.trip_direction = trip_direction
        changed = True
    if trip_group and manifest_doc.get("trip_group") != trip_group:
        manifest_doc.trip_group = trip_group
        changed = True

    return changed


def _local_seconds(stamp):
    """A stored UTC timeline stamp as seconds past midnight in the site's timezone.

    Rows carry UTC (``2026-08-18T11:15:00.000Z``) while the shift times, the QOA report
    time and everything a driver reads are local, so the two have to be reconciled once,
    here, rather than in each caller.
    """
    if not stamp:
        return None
    try:
        import pytz

        text = str(stamp).replace("T", " ").replace("Z", "").split(".")[0]
        utc = pytz.utc.localize(frappe.utils.get_datetime(text))
        site_tz = pytz.timezone(frappe.db.get_single_value("System Settings", "time_zone") or "UTC")
        local = utc.astimezone(site_tz)
        return local.hour * 3600 + local.minute * 60 + local.second
    except Exception:
        return None


def _time_field(seconds):
    """Seconds past midnight as ``HH:MM:SS`` for a Time column, or None."""
    if seconds is None:
        return None
    seconds = int(seconds) % 86400
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def _stamp_leg_details(doc, leg_timings=None):
	"""Write each leg's own facts onto its assignment row (WI-002151, WI-002171).

	The row stays one per card - that is what carries the shipment link and the roster -
	but the numbers on it come from the run's physical stops, which is what the bus
	actually does and what the trip modal shows. A card is served at one stop: an
	outward card where its riders are put down, a return card where they are collected.
	That stop's index, action and running load are what the row records, so the plan, the
	modal and the manifest all describe the same run.

	QOA stays with the outward rows: their riders report at the camp they board from, and
	the camp stop itself has no row of its own. Only the first card out of a given camp
	reports - riders from two cards at one camp board together, once.
	"""
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
		CAMP_STOP,
		arrival_order,
		build_itinerary,
		own_direction,
		walk_occupancy,
	)

	def _boards(card):
		return own_direction(card) == "RETURN"
	from one_fm.operations.doctype.route_plan.route_plan import _cards_for_itinerary

	# Rebuilt from scratch every save: a camp leg is derived from the run, so a stale one
	# left behind by a card that has since moved would describe a stop the bus no longer
	# makes. The card rows are the input.
	doc.assignments = [row for row in doc.assignments if not cint(row.is_camp_leg)]
	rows = [row for row in doc.assignments if row.vehicle]
	if not rows:
		return

	camp_legs = []

	limits = {
		v.name: passenger_capacity(v.seats, v.custom_includes_driver_seat)
		for v in frappe.get_all(
			"Vehicle",
			filters={"name": ["in", list({row.vehicle for row in rows})]},
			fields=["name", "seats", "custom_includes_driver_seat"],
		)
	}
	buffer_minutes = qoa_buffer_minutes()

	runs = {}
	for row in rows:
		runs.setdefault((row.vehicle, row.trip_group or f"\0{row.card_id}"), []).append(row)

	for (vehicle, _group), run in runs.items():
		group_key = _group if not _group.startswith("\0") else run[0].card_id
		cards = _cards_for_itinerary(run)
		by_name = {card.name: card for card in cards}
		ordered = sorted(
			[row for row in run if row.transportation_shipment in by_name],
			key=lambda row: arrival_order(by_name[row.transportation_shipment]),
		)
		if not ordered:
			continue

		itinerary = build_itinerary([by_name[row.transportation_shipment] for row in ordered])
		_peak, _worst, per_stop = walk_occupancy(itinerary)

		# The stop that serves each card: an outward card where its riders are put down,
		# a return card where they are collected. A return card also appears at the home
		# stop, where it is only being delivered - taking that one would file every
		# return leg against the ride home.
		serves = {}
		for position, stop in enumerate(itinerary):
			if stop["kind"] == CAMP_STOP:
				continue
			for card in stop["dropping"]:
				if not _boards(card):
					serves[card.name] = (stop, per_stop[position])
			for card in stop["boarding"]:
				serves[card.name] = (stop, per_stop[position])

		# The first card out of each camp, and when the bus leaves that camp - which is
		# the earliest leg belonging to a card boarding there, not this card's own.
		camp_first, camp_departs = {}, {}
		for stop in itinerary:
			if stop["kind"] != CAMP_STOP or stop["place"] in camp_first:
				continue
			boarding = [card.name for card in stop["boarding"]]
			camp_first[stop["place"]] = boarding[0] if boarding else None
			leaving = [
				_local_seconds(row.start_time) for row in ordered
				if row.transportation_shipment in boarding and _local_seconds(row.start_time) is not None
			]
			camp_departs[stop["place"]] = min(leaving) if leaving else None

		for row in ordered:
			card = by_name[row.transportation_shipment]
			boards = _boards(card)
			served = serves.get(card.name)
			if not served:
				continue
			stop, onboard = served

			row.max_passenger_capacity = limits.get(vehicle) or 0
			row.stop_index = stop["stop_index"]
			row.action_type = stop["action_type"]
			row.current_passenger_count = onboard
			row.boarding_count = cint(row.headcount) if boards else 0
			row.drop_off_count = 0 if boards else cint(row.headcount)
			row.is_accommodation_origin = 0 if boards else 1
			origin = stop["place"] if boards else _camp_place_for(card)
			row.origin_location = (
				origin if origin and frappe.db.exists("Location", origin) else None
			)
			row.shift_start_time = card.start_time
			departs = _local_seconds(row.start_time)
			arrives = _local_seconds(row.end_time)
			row.is_next_day = (
				1 if (departs is not None and arrives is not None and arrives < departs) else 0
			)
			# The camp reports before the run leaves IT, not before this card's own leg.
			place = None if boards else _camp_place_for(card)
			row.qoa_time = None
			if place and camp_first.get(place) == card.name and camp_departs.get(place) is not None:
				row.qoa_time = _time_field(camp_departs[place] - buffer_minutes * 60)

		camp_legs.extend(_camp_leg_rows(itinerary, ordered, per_stop, vehicle,
										camp_departs, buffer_minutes, limits, group_key,
										(leg_timings or {}).get(group_key, {})))

	for values in camp_legs:
		doc.append("assignments", values)


CAMP_LEG_PREFIX = "CAMPLEG"


def camp_leg_group(card_id) -> str:
	"""The run a camp leg belongs to, read back out of its card id."""
	return str(card_id or "").split("|")[1] if "|" in str(card_id or "") else ""


def _camp_leg_rows(itinerary, ordered, per_stop, vehicle, camp_departs,
				   buffer_minutes, limits, group_key, minutes=None) -> list:
	"""The rows for the stops no card is filed against: the camps the bus loads at.

	A card row records the leg out of the stop that SERVES it - where an outward card's
	riders are put down, where a return card's are collected. Nothing serves a camp, so
	the drive out of it had nowhere to be recorded: the Trip Builder accepted minutes for
	it and the plan forgot them, and re-opening the run put that leg back on a default
	nobody chose, moving every stop after it.

	The shipment link is filled in from the first card boarding there, so the row can be
	traced back to a journey, but the row is a description of the run and never a
	placement - `card_rows` keeps it out of every count and every itinerary.
	"""
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import CAMP_STOP

	rows = []
	seen = set()
	first = ordered[0]
	for position, stop in enumerate(itinerary):
		if stop["kind"] != CAMP_STOP or stop["place"] in seen:
			continue
		seen.add(stop["place"])
		boarding = [card.name for card in stop["boarding"]]
		serving = next((row for row in ordered if row.transportation_shipment in boarding), None)
		departs = camp_departs.get(stop["place"])
		held = (minutes or {}).get(stop["place"]) or {}
		rows.append({
			"card_id": f"{CAMP_LEG_PREFIX}|{group_key}|{stop['stop_index']}",
			"is_camp_leg": 1,
			"transportation_shipment": serving.transportation_shipment if serving else None,
			"vehicle": vehicle,
			"direction": (serving or first).direction,
			"trip_group": (serving or first).trip_group,
			"trip_name": (serving or first).trip_name,
			"stop_index": stop["stop_index"],
			"action_type": stop["action_type"],
			"origin_location": (
				stop["place"] if frappe.db.exists("Location", stop["place"]) else None
			),
			"stop_location": stop["place"],
			"accommodation": stop["place"],
			"is_accommodation_origin": 1,
			"boarding_count": stop["boarding_count"],
			"drop_off_count": stop["drop_off_count"],
			"current_passenger_count": per_stop[position],
			"max_passenger_capacity": limits.get(vehicle) or 0,
			# Not a placement: a camp row that carried riders would count them a second
			# time in every report that sums the column.
			"headcount": 0,
			"start_time": (serving or first).start_time,
			"end_time": (serving or first).end_time,
			"transit_minutes": cint(held.get("transit_minutes")),
			"buffer_minutes": cint(held.get("buffer_minutes")),
			"qoa_time": (
				_time_field(departs - buffer_minutes * 60) if departs is not None else None
			),
		})
	return rows


def _camp_place_for(card):
	"""The Location standing for a card's camp, or its readable name."""
	if not card.accommodation:
		return None
	return frappe.db.get_value(
		"Accommodation", card.accommodation, "transport_stop_location"
	) or card.accommodation_name or card.accommodation
