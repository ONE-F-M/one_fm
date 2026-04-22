import frappe
import requests
from frappe import _

PICKUP_BUFFER = 10             # minutes
MAX_TRANSIT = 60               # minutes

def get_context(context):
    pass

@frappe.whitelist()
def get_route_planner_data():
    try:
        import pytz
        from datetime import timedelta

        # ── Time bounds (same logic as optimize_transportation_routes) ──
        site_tz = pytz.timezone(frappe.db.get_single_value("System Settings", "time_zone") or "UTC")
        local_today_start = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 00:00:00")) - timedelta(hours=6)
        local_today_end   = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 23:59:59")) + timedelta(hours=6)
        global_start_utc  = local_today_start.astimezone(pytz.utc).replace(tzinfo=None)
        global_end_utc    = local_today_end.astimezone(pytz.utc).replace(tzinfo=None)

        def fmt(dt):
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── 1. Vehicles ──────────────────────────────────────────────────
        transport_vehicles = frappe.get_all("Vehicle",
            filters={"transport_stop_vehicle": 1},
            fields=["name", "location", "seats", "one_fm_vehicle_type", "make", "employee"],
            order_by="name asc"
        )

        MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

        vehicles = []
        for v in transport_vehicles:
            coords = get_coords("Location", v.location)
            if not coords:
                continue

            driver_name = "—"
            if v.employee:
                driver_name = frappe.db.get_value("Employee", v.employee, "employee_name") or "—"

            acc_name = frappe.db.get_value("Accommodation",
                {"transport_stop_location": v.location},
                "accommodation"
            ) or v.location
            if acc_name in MAHBOULA_LABELS:
                acc_name = "Mahboula Camp"

            vehicles.append({
                "id":            v.name,
                "label":         v.name,
                "driver":        driver_name,
                "seats":         v.seats or 0,
                "type":          v.one_fm_vehicle_type or "—",
                "make":          v.make or "—",
                "accommodation": acc_name,
                "location":      v.location,
                "coords":        {"lat": coords[0], "lng": coords[1]}
            })

        # ── 2. Shipment cards ────────────────────────────────────────────
        nested_map = get_grouped_employees_by_accommodation()

        # Batch resolve all employee names up front
        all_emp_ids = set()
        for acc_data in nested_map.values():
            for emp_list in acc_data["shifts"].values():
                all_emp_ids.update(emp_list)

        emp_name_map = {
            e.name: e.employee_name
            for e in frappe.get_all("Employee",
                filters={"name": ["in", list(all_emp_ids)]},
                fields=["name", "employee_name"]
            )
        }

        shipment_cards = []

        for acc_name, acc_data in nested_map.items():
            lookup_id  = acc_data["lookup_id"]
            acc_coords = get_coords("Accommodation", lookup_id)
            if not acc_coords:
                continue

            olm_groups = {}

            for shift_name, employee_list in acc_data["shifts"].items():
                shift_doc        = frappe.get_doc("Operations Shift", shift_name)
                operations_site  = shift_doc.site
                headcount        = len(employee_list)

                # Resolve site location display name
                site_location = frappe.db.get_value("Operations Site", operations_site, "site_location") or operations_site

                # Resolve expected arrival
                expected_arrival = getattr(shift_doc, "expected_arrival_time_at_site", None)
                def to_utc(dt_str):
                    import pytz
                    dt = frappe.utils.get_datetime(f"{frappe.utils.today()} {dt_str}")
                    tz = pytz.timezone(frappe.db.get_single_value("System Settings", "time_zone") or "UTC")
                    return tz.localize(dt).astimezone(pytz.utc).replace(tzinfo=None)

                start_utc = to_utc(shift_doc.start_time)
                end_utc   = to_utc(shift_doc.end_time)

                if expected_arrival and str(expected_arrival) != str(shift_doc.start_time):
                    effective_start_utc = to_utc(expected_arrival)
                    outbound_window_start = fmt(effective_start_utc)
                    outbound_window_end   = fmt(effective_start_utc)
                else:
                    outbound_window_start = fmt(start_utc - timedelta(minutes=PICKUP_BUFFER))
                    outbound_window_end   = fmt(start_utc)

                employees_named = [emp_name_map.get(e, e) for e in employee_list]

                # ── OSM ──
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
                    base_h   = headcount // num_locs
                    extra_h  = headcount % num_locs
                    emp_idx  = 0

                    for i, loc in enumerate(all_osm_locations):
                        current_h     = base_h + (1 if i < extra_h else 0)
                        loc_employees = employee_list[emp_idx:emp_idx + current_h]
                        emp_idx      += current_h
                        if current_h == 0:
                            continue

                        card_id = f"{acc_name}_{shift_name}_{loc['name']}"
                        shipment_cards.append({
                            "id":                   card_id,
                            "accommodation":        acc_name,
                            "accommodation_coords": {"lat": acc_coords[0], "lng": acc_coords[1]},
                            "shift_name":           shift_name,
                            "site":                 operations_site,
                            "site_location":        site_location,
                            "stop_location":        loc["name"],
                            "stop_coords":          {"lat": loc["coords"][0], "lng": loc["coords"][1]},
                            "headcount":            current_h,
                            "employees":            [emp_name_map.get(e, e) for e in loc_employees],
                            "outbound_window_start": outbound_window_start,
                            "outbound_window_end":   outbound_window_end,
                            "return_window_start":   fmt(end_utc),
                            "return_window_end":     fmt(end_utc + timedelta(minutes=PICKUP_BUFFER)),
                            "shift_start":           fmt(start_utc),
                            "shift_end":             fmt(end_utc),
                            "type":                 "OSM"
                        })

                # ── OLM ──
                one_location_many_sites = frappe.db.sql("""
                    SELECT parent FROM `tabLocation To Site Mapping` WHERE sites = %s
                """, (operations_site,), as_dict=True)

                for olm in one_location_many_sites:
                    olm_doc = frappe.get_doc("Site Transport Stop Location", olm.parent)
                    if olm_doc.site_arrangement != "One Location Many Sites":
                        continue

                    stop_location = olm_doc.transport_stop_location
                    start_dt      = frappe.utils.get_datetime(f"2000-01-01 {shift_doc.start_time}")
                    time_key      = start_dt.hour
                    group_key     = (stop_location, time_key)

                    if group_key not in olm_groups:
                        olm_groups[group_key] = {
                            "shifts":    [],
                            "headcount": 0,
                            "employees": []
                        }
                    olm_groups[group_key]["shifts"].append(shift_doc)
                    olm_groups[group_key]["headcount"] += headcount
                    olm_groups[group_key]["employees"].extend(employee_list)

            # ── OLM cards ──
            for group_key, group_data in olm_groups.items():
                stop_location, time_key = group_key
                stop_coords = get_coords("Location", stop_location)
                if not stop_coords:
                    continue

                shifts         = group_data["shifts"]
                earliest_start = min(s.start_time for s in shifts)
                latest_end     = max(s.end_time for s in shifts)
                start_utc      = to_utc(earliest_start)
                end_utc        = to_utc(latest_end)

                site_locations = sorted({
                    frappe.db.get_value("Operations Site", s.site, "site_location") or s.site
                    for s in shifts
                })
                real_shift_names = " · ".join(sorted(set(s.name for s in shifts)))

                card_id = f"{acc_name}_Grouped_{stop_location}_{time_key}"
                shipment_cards.append({
                    "id":                   card_id,
                    "accommodation":        acc_name,
                    "accommodation_coords": {"lat": acc_coords[0], "lng": acc_coords[1]},
                    "shift_name":           real_shift_names,
                    "site":                 " · ".join(sorted(set(s.site for s in shifts))),
                    "site_location":        " · ".join(site_locations),
                    "stop_location":        stop_location,
                    "stop_coords":          {"lat": stop_coords[0], "lng": stop_coords[1]},
                    "headcount":            group_data["headcount"],
                    "employees":            [emp_name_map.get(e, e) for e in group_data["employees"]],
                    "outbound_window_start": fmt(start_utc - timedelta(minutes=PICKUP_BUFFER)),
                    "outbound_window_end":   fmt(start_utc),
                    "return_window_start":   fmt(end_utc),
                    "return_window_end":     fmt(end_utc + timedelta(minutes=PICKUP_BUFFER)),
                    "shift_start":           fmt(start_utc),
                    "shift_end":             fmt(end_utc),
                    "type":                 "OLM"
                })

        return {
            "status":         "ok",
            "date":           frappe.utils.today(),
            "global_start":   fmt(global_start_utc),
            "global_end":     fmt(global_end_utc),
            "vehicles":       vehicles,
            "shipment_cards": shipment_cards
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
        local_today_start = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 00:00:00")) - timedelta(hours=6)
        local_today_end = site_tz.localize(frappe.utils.get_datetime(frappe.utils.today() + " 23:59:59")) + timedelta(hours=6)
        
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

    accommodation_map = {}
    for emp in employees:
        # 3. For each employee, look up their current accommodation record ID
        latest_checkin = frappe.db.get_value("Accommodation Checkin Checkout", 
            {"employee": emp.name, "type": "IN"}, 
            ["name", "accommodation"],
            order_by="creation desc",
            as_dict=True
        )

        if not latest_checkin:
            frappe.log_error(f"{emp.name} has no checkin record", "Route Optimization")
            continue

        acc_id = latest_checkin.accommodation
        acc_label = frappe.db.get_value("Accommodation", acc_id, "accommodation")
        
        if not acc_label:
            continue
        
        # 4. Handle Mahboula buildings grouping (3, 12, 13, 15)
        # We group them under "Mahboula Camp" but keep a valid acc_id for location lookups
        acc_key = "Mahboula Camp" if acc_label in ["Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"] else acc_id
            
        if acc_key not in accommodation_map:
            accommodation_map[acc_key] = {
                "lookup_id": acc_id,
                "employees": []
            }
        
        accommodation_map[acc_key]["employees"].append(emp)

    # Group by shift under accommodation
    nested_map = {}
    for acc_key, data in accommodation_map.items():
        lookup_id = data["lookup_id"]
        emp_list = data["employees"]
        
        # 5. Only consider Accommodation entries that have the "Stop Location" field populated.
        acc_doc = frappe.db.get_value("Accommodation", lookup_id, ["name", "transport_stop_location"], as_dict=True)
        
        if not acc_doc or not acc_doc.transport_stop_location:
            continue

        nested_map[acc_key] = {
            "lookup_id": lookup_id,
            "shifts": {}
        }
        for emp in emp_list:
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
        e.name: e.employee_name
        for e in frappe.get_all("Employee",
            filters={"name": ["in", list(all_emp_ids)]},
            fields=["name", "employee_name"]
        )
    }
    shipment_employees_named = {
        label: [emp_name_map.get(eid, eid) for eid in eids]
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
        fields=["name", "location", "seats", "one_fm_vehicle_type", "make", "employee"],
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
            "loadLimits":    {"seats": {"maxLoad": max((v.seats or 1) - 1, 1)}},
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