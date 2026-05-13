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
            fields=["name", "location", "seats", "one_fm_vehicle_type", "make", "employee"],
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

        # Batch-fetch all shift docs in one query (instead of per-shift frappe.get_doc)
        all_shift_names = set()
        for acc_data in nested_map.values():
            all_shift_names.update(acc_data["shifts"].keys())

        shift_doc_map = {}
        if all_shift_names:
            for s in frappe.get_all("Operations Shift",
                filters={"name": ["in", list(all_shift_names)]},
                fields=["name", "site", "start_time", "end_time", "expected_arrival_time_at_site"]
            ):
                shift_doc_map[s.name] = s

        # Batch-fetch all site locations in one query
        all_sites = list({s.site for s in shift_doc_map.values() if s.site})
        site_location_map = {}
        if all_sites:
            for row in frappe.get_all("Operations Site",
                filters={"name": ["in", all_sites]},
                fields=["name", "site_location"]
            ):
                site_location_map[row.name] = row.site_location or row.name

        # Batch-fetch all OSM mappings in two queries (parent + child)
        osm_by_site = {}
        if all_sites:
            osm_records = frappe.get_all("Site Transport Stop Location",
                filters={"site_arrangement": "One Site Many Locations", "site": ["in", all_sites]},
                fields=["name", "site"]
            )
            if osm_records:
                osm_parent_names = [r.name for r in osm_records]
                osm_child_rows = frappe.get_all("Site To Location Mapping",
                    filters={"parent": ["in", osm_parent_names]},
                    fields=["parent", "location"]
                )
                osm_site_lookup = {r.name: r.site for r in osm_records}
                for child in osm_child_rows:
                    site = osm_site_lookup.get(child.parent)
                    if site:
                        coords = get_coords_cached("Location", child.location)
                        if coords:
                            osm_by_site.setdefault(site, []).append({"name": child.location, "coords": coords})

        # Batch-fetch all OLM mappings in two queries
        # Filter at DB level by sites IN all_sites (fix #1: avoid loading all rows)
        olm_by_site = {}
        olm_doc_map = {}
        if all_sites:
            olm_child_rows = frappe.get_all("Location To Site Mapping",
                filters={"parenttype": "Site Transport Stop Location", "sites": ["in", all_sites]},
                fields=["parent", "sites"]
            )
            olm_parent_names = set()
            for child in olm_child_rows:
                olm_by_site.setdefault(child.sites, []).append(child.parent)
                olm_parent_names.add(child.parent)
            if olm_parent_names:
                for doc in frappe.get_all("Site Transport Stop Location",
                    filters={"name": ["in", list(olm_parent_names)], "site_arrangement": "One Location Many Sites"},
                    fields=["name", "transport_stop_location"]
                ):
                    olm_doc_map[doc.name] = doc

        # ── Build shipment cards ──
        shipment_cards = []

        for acc_name, acc_data in nested_map.items():
            lookup_id  = acc_data["lookup_id"]
            acc_coords = get_coords_cached("Accommodation", lookup_id)
            if not acc_coords:
                continue

            olm_groups = {}

            for shift_name, employee_list in acc_data["shifts"].items():
                shift_doc = shift_doc_map.get(shift_name)
                if not shift_doc:
                    continue

                operations_site = shift_doc.site
                headcount       = len(employee_list)
                site_location   = site_location_map.get(operations_site, operations_site)

                start_utc = to_utc(shift_doc.start_time)
                end_utc   = to_utc(shift_doc.end_time)

                # Expected arrival logic
                expected_arrival = shift_doc.expected_arrival_time_at_site
                use_expected = False
                if expected_arrival and str(expected_arrival) != str(shift_doc.start_time):
                    effective_start_utc = to_utc(expected_arrival)
                    if effective_start_utc < end_utc:
                        use_expected = True

                if use_expected:
                    outbound_window_start = fmt(effective_start_utc)
                    outbound_window_end   = fmt(effective_start_utc)
                else:
                    outbound_window_start = fmt(start_utc - timedelta(minutes=PICKUP_BUFFER))
                    outbound_window_end   = fmt(start_utc)

                employees_named = [emp_name_map.get(e, e) for e in employee_list]

                handled = False

                # ── OSM (pre-fetched) ──
                all_osm_locations = osm_by_site.get(operations_site, [])

                # (handled already set above)

                if all_osm_locations:
                    handled = True
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

                # ── OLM (pre-fetched) ──
                olm_parents = olm_by_site.get(operations_site, [])
                for parent_name in olm_parents:
                    olm_doc = olm_doc_map.get(parent_name)
                    if not olm_doc:
                        continue

                    handled = True
                    stop_location = olm_doc.transport_stop_location
                    start_dt      = frappe.utils.get_datetime(f"2000-01-01 {shift_doc.start_time}")
                    time_key      = start_dt.hour
                    group_key     = (stop_location, time_key)

                    if group_key not in olm_groups:
                        olm_groups[group_key] = {
                            "shifts":    [],
                            "headcount": 0,
                            "employees": [],
                            "shift_employees": {}  # shift_name → [emp_ids] for accurate per-site count
                        }
                    olm_groups[group_key]["shifts"].append(shift_doc)
                    olm_groups[group_key]["headcount"] += headcount
                    olm_groups[group_key]["employees"].extend(employee_list)
                    olm_groups[group_key]["shift_employees"][shift_name] = employee_list

                # ── Default fallback: DIRECT ──
                if not handled:
                    site_loc_name = site_location_map.get(operations_site)
                    site_coords = get_coords_cached("Location", site_loc_name) if site_loc_name else None
                    if site_coords:
                        card_id = f"{acc_name}_{shift_name}_{site_loc_name}"
                        shipment_cards.append({
                            "id":                   card_id,
                            "accommodation":        acc_name,
                            "accommodation_coords": {"lat": acc_coords[0], "lng": acc_coords[1]},
                            "shift_name":           shift_name,
                            "site":                 operations_site,
                            "site_location":        site_location,
                            "stop_location":        site_loc_name,
                            "stop_coords":          {"lat": site_coords[0], "lng": site_coords[1]},
                            "headcount":            headcount,
                            "employees":            employees_named,
                            "outbound_window_start": outbound_window_start,
                            "outbound_window_end":   outbound_window_end,
                            "return_window_start":   fmt(end_utc),
                            "return_window_end":     fmt(end_utc + timedelta(minutes=PICKUP_BUFFER)),
                            "shift_start":           fmt(start_utc),
                            "shift_end":             fmt(end_utc),
                            "type":                 "DIRECT"
                        })

            # ── OLM cards ──
            for group_key, group_data in olm_groups.items():
                stop_location, time_key = group_key
                stop_coords = get_coords_cached("Location", stop_location)
                if not stop_coords:
                    continue

                shifts         = group_data["shifts"]
                earliest_start = min(s.start_time for s in shifts)
                latest_end     = max(s.end_time for s in shifts)
                start_utc      = to_utc(earliest_start)
                end_utc        = to_utc(latest_end)

                site_locations = sorted({
                    site_location_map.get(s.site, s.site)
                    for s in shifts
                })
                real_shift_names = " · ".join(sorted(set(s.name for s in shifts)))

                card_id = f"{acc_name}_Grouped_{stop_location}_{time_key}"

                # Build per-site breakdown for OLM detail display
                # Fix #2: use site_location_map (already batch-fetched) instead of N+1 db.get_value
                # Fix #3: use shift_employees map for accurate per-site headcount
                site_breakdown = []
                site_shift_map = {}
                shift_employees = group_data.get("shift_employees", {})
                for s in shifts:
                    site_name = s.site
                    if site_name not in site_shift_map:
                        site_shift_map[site_name] = {
                            "site": site_name,
                            "site_location": site_location_map.get(site_name, site_name),
                            "shifts": [],
                            "employee_count": 0
                        }
                    site_shift_map[site_name]["shifts"].append(s.name)
                # Count employees per site using only shifts that belong to that site
                for site_name, info in site_shift_map.items():
                    site_emps = set()
                    for s in shifts:
                        if s.site == site_name:
                            site_emps.update(shift_employees.get(s.name, []))
                    info["employee_count"] = len(site_emps)
                    site_breakdown.append(info)

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
                    "type":                 "OLM",
                    "sites":                site_breakdown
                })

        # ── Cross-reference: find return-leg employees (previous shift at same stop) ──
        # For each card, find employees from a DIFFERENT shift at the same stop_location
        # whose shift ends around the time this card's shift starts.
        # These are the employees finishing their shift who need to be picked up.
        from datetime import datetime as dt_cls

        def parse_iso(s):
            try:
                return dt_cls.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                return None

        # Build stop_location → [card] index
        stop_cards = {}
        for card in shipment_cards:
            sl = card.get("stop_location", "")
            if sl:
                if sl not in stop_cards:
                    stop_cards[sl] = []
                stop_cards[sl].append(card)

        # For each card, find the "previous shift" card at the same stop
        for card in shipment_cards:
            sl = card.get("stop_location", "")
            card_shift_start = parse_iso(card.get("shift_start", ""))
            if not sl or not card_shift_start:
                card["return_employees"] = []
                continue

            best_match = None
            best_gap = float("inf")

            for other in stop_cards.get(sl, []):
                if other["id"] == card["id"]:
                    continue  # skip self
                if other.get("shift_name") == card.get("shift_name"):
                    continue  # skip same shift

                if other.get("accommodation") != card.get("accommodation"):
                    continue

                other_shift_end = parse_iso(other.get("shift_end", ""))
                if not other_shift_end:
                    continue

                # How close is other's shift_end to this card's shift_start?
                diff_seconds = (card_shift_start - other_shift_end).total_seconds()
                
                # other_shift_end should be around the same time as card_shift_start, or ANY TIME BEFORE it.
                # Allow shift to end up to 1 hour after dropoff (vehicle waits for them)
                # No upper limit on how long ago the shift ended (they wait for vehicle)
                if -3600 <= diff_seconds:
                    gap = abs(diff_seconds)
                    if gap < best_gap:
                        best_gap = gap
                        best_match = other

            if best_match:
                card["return_employees"] = best_match.get("employees", [])
            else:
                card["return_employees"] = []

        # ── Split each card into OUTBOUND + RETURN direction-specific cards ──
        # This gives the dispatcher two separate draggable items per shift×stop
        expanded_cards = []
        for card in shipment_cards:
            original_id = card["id"]

            # Outbound card — employees going TO the site
            out_card = {**card}
            out_card["id"] = f"{original_id}_OUT"
            out_card["direction"] = "OUTBOUND"
            out_card["shift_direction_label"] = "\u2192 Outbound (To Site)"
            out_card["pair_id"] = original_id  # links OUT ↔ RET
            expanded_cards.append(out_card)

            # Return card — employees coming BACK from the site
            ret_employees = card.get("return_employees", [])
            ret_card = {**card}
            ret_card["id"] = f"{original_id}_RET"
            ret_card["direction"] = "RETURN"
            ret_card["shift_direction_label"] = "\u2190 Return (From Site)"
            ret_card["pair_id"] = original_id  # links OUT ↔ RET
            ret_card["headcount"] = len(ret_employees) if ret_employees else card["headcount"]
            ret_card["employees"] = ret_employees if ret_employees else card["employees"]
            expanded_cards.append(ret_card)

        shipment_cards = expanded_cards

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
        fields=["name", "title", "status", "effective_from", "effective_until"],
        order_by="creation desc"
    )
    return plans


@frappe.whitelist()
def save_assignments(plan_name: str, swim_items: str, assigned_cards: str):
    """Save route planner swim items into a Route Plan DocType."""
    if not _route_plan_exists():
        frappe.throw(_("Route Plan DocType not found. Please run 'bench migrate' on this site first."))

    import json
    items = json.loads(swim_items)
    cards = json.loads(assigned_cards)

    doc = frappe.get_doc("Route Plan", plan_name)
    doc.check_permission("write")

    # Clear existing assignments and rebuild
    doc.assignments = []
    for item in items:
        doc.append("assignments", {
            "card_id":       item.get("cardId", ""),
            "vehicle":       item.get("vehicleId", ""),
            "direction":     item.get("direction", ""),
            "stop_index":    item.get("stopIndex", 0),
            "trip_group":    item.get("tripId", ""),
            "headcount":     item.get("headcount", 0),
            "start_time":    item.get("start", ""),
            "end_time":      item.get("end", ""),
            "site":          item.get("_site", ""),
            "shift":         item.get("_shift", ""),
            "accommodation": item.get("_accommodation", ""),
            "stop_location": item.get("_stopLocation", ""),
        })

    doc.save(ignore_permissions=False)

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
        plan_name = frappe.db.get_value("Route Plan", {"status": "Active"}, "name")

    if not plan_name:
        return {"status": "empty"}

    doc = frappe.get_doc("Route Plan", plan_name)
    doc.check_permission("read")

    swim_items = []
    assigned_card_ids = set()

    for row in doc.assignments:
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
            "stopIndex": row.stop_index or 0,
            "totalStops": 0,  # recalculated client-side
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
        "plan_name": doc.name,
        "plan_title": doc.title,
        "plan_status": doc.status,
        "effective_from": str(doc.effective_from) if doc.effective_from else None,
        "effective_until": str(doc.effective_until) if doc.effective_until else None,
        "swim_items": swim_items,
        "assigned_cards": list(assigned_card_ids),
        "saved_by": doc.last_modified_by_user,
        "saved_at": str(doc.last_modified_at) if doc.last_modified_at else None
    }


@frappe.whitelist()
def create_route_plan(title: str, effective_from: str, effective_until: str = ""):
    """Create a new Route Plan and return its name."""
    if not _route_plan_exists():
        frappe.throw(_("Route Plan DocType not found. Please run 'bench migrate' on this site first."))

    doc = frappe.new_doc("Route Plan")
    doc.title = title
    doc.effective_from = effective_from
    doc.effective_until = effective_until or None
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