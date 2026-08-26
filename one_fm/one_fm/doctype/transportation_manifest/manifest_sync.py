# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""
Transportation Manifest sync utilities.

Contains the manifest detail upsert logic extracted for testability
and reuse across the schedule page backend and any future callers.
"""


def sync_manifest_details(manifest_doc, assignment_rows, emp_map, return_emp_map):
	"""Upsert child rows using compound key: (employee, trip_id, stop_id, employee_action).

	New employees/stops are appended. Existing rows have system fields refreshed
	while manual dispatcher fields (attendance, QOA, reliever) are preserved.
	Rows no longer present in the plan are left as-is (preserves manual data).

	Args:
		manifest_doc: A Transportation Manifest document (new or existing).
		assignment_rows: List of Route Plan Assignment child rows for this vehicle.
		emp_map: Dict mapping card_id -> list of employee dicts (OUTBOUND).
		return_emp_map: Dict mapping card_id -> list of employee dicts (RETURN).

	Returns:
		True if any rows were added or updated.
	"""
	changed = False

	# Build lookup index of existing rows by compound key.
	# For pre-existing rows with empty stop_id, derive it from stop_name + employee_action
	# to prevent duplicate inserts during the migration period.
	existing_index = {}
	# Secondary index for legacy rows with empty trip_id — keyed without trip_id
	legacy_index = {}

	for row in manifest_doc.transportation_manifest_details:
		if row.stop_id:
			stop_id_for_key = row.stop_id
		else:
			# Derive stop_id from existing data for backward compatibility
			direction = "RETURN" if row.employee_action == "Dropping Off" else "OUTBOUND"
			stop_id_for_key = f"{row.stop_name or ''}|{direction}"

		key = (row.employee or "", row.trip_id or "", stop_id_for_key, row.employee_action or "")
		existing_index[key] = row

		# Also index by (employee, stop_id, action) without trip_id for legacy matching
		if not row.trip_id:
			legacy_key = (row.employee or "", stop_id_for_key, row.employee_action or "")
			legacy_index[legacy_key] = row

	# Collect employees already serving as relievers to avoid creating duplicate rows
	# when a reliever is also listed in the route plan's employee map
	active_relievers = {
		row.reliever_employee
		for row in manifest_doc.transportation_manifest_details
		if row.reliever_employee
	}

	for a_row in assignment_rows:
		direction = a_row.direction
		emps = (return_emp_map if direction == "RETURN" else emp_map).get(a_row.card_id, [])
		# Two frames, deliberately both recorded. `employee_action` says what this rider
		# does at the PICKUP CAMP - an outward rider boards there, a return rider is
		# dropped there - and the attendance-check lock keys off it. `stop_action` says
		# what happens to the same rider AT THIS STOP, which is the opposite and is what
		# the driver needs at a handover: outward riders get off, return riders get on
		# (WI-002171 AC 3.5).
		action = "Dropping Off" if direction == "RETURN" else "Boarding"
		stop_action = "Boarding" if direction == "RETURN" else "Dropping Off"
		stop_id_val = f"{a_row.stop_location or ''}|{direction}"

		for emp in emps:
			emp_id = emp.get("id")
			if not emp_id:
				continue

			# Skip employees already serving as relievers on another row
			# to avoid creating duplicate manifest entries
			if emp_id in active_relievers:
				continue

			# Parse scheduled time from ISO timestamp
			time_str = a_row.end_time if direction == "RETURN" else a_row.start_time
			if time_str and "T" in time_str:
				time_str = time_str.split("T")[1][:8]

			key = (emp_id, a_row.trip_group or "", stop_id_val, action)
			legacy_key = (emp_id, stop_id_val, action)

			# Primary lookup: full compound key
			matched_row = existing_index.get(key)

			# Fallback: legacy rows with empty trip_id
			if not matched_row and legacy_key in legacy_index:
				matched_row = legacy_index[legacy_key]

			if matched_row:
				# UPDATE: refresh system fields, preserve manual fields
				row = matched_row
				new_stop_name = a_row.stop_location or ""
				new_stop_type = "Return" if direction == "RETURN" else "Pick Up"
				new_trip_name = a_row.trip_name or ""
				new_emp_name = emp.get("name", "")

				# Detect if any system field actually changed
				if (
					(row.stop_name or "") != new_stop_name
					or (row.stop_type or "") != new_stop_type
					or str(row.scheduled_time or "") != str(time_str or "")
					or (row.trip_name or "") != new_trip_name
					or (row.employee_name or "") != new_emp_name
				):
					changed = True

				# Backfilled on every sync so the 4,633 rows written before this field
				# existed pick it up without a separate migration.
				if (row.stop_action or "") != stop_action:
					row.stop_action = stop_action
					changed = True

				row.stop_name = new_stop_name
				row.stop_type = new_stop_type
				row.scheduled_time = time_str
				row.trip_name = new_trip_name
				row.employee_name = new_emp_name
				# Backfill stop_id for pre-existing rows
				if not row.stop_id or row.stop_id != stop_id_val:
					row.stop_id = stop_id_val
					changed = True
				# Backfill trip_id for legacy rows
				if not row.trip_id and (a_row.trip_group or ""):
					row.trip_id = a_row.trip_group
					changed = True
				# DO NOT touch: attendance_status, qoa_status, qoa_reason,
				#               requires_reliever, reliever_employee
			else:
				# INSERT: new child row
				manifest_doc.append("transportation_manifest_details", {
					"stop_name": a_row.stop_location or "",
					"employee": emp_id,
					"employee_name": emp.get("name", ""),
					"trip_id": a_row.trip_group or "",
					"trip_name": a_row.trip_name or "",
					"stop_id": stop_id_val,
					"stop_type": "Return" if direction == "RETURN" else "Pick Up",
					"employee_action": action,
					"stop_action": stop_action,
					"scheduled_time": time_str,
					"requires_reliever": 0,
				})
				changed = True

	return changed
