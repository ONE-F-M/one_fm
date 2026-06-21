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
	Rows no longer present in the plan are flagged as 'Removed' but kept.

	Args:
		manifest_doc: A Transportation Manifest document (new or existing).
		assignment_rows: List of Route Plan Assignment child rows for this vehicle.
		emp_map: Dict mapping card_id -> list of employee dicts (OUTBOUND).
		return_emp_map: Dict mapping card_id -> list of employee dicts (RETURN).

	Returns:
		True if any rows were added, updated, or flagged.
	"""
	changed = False

	# Build lookup index of existing rows by compound key.
	# For pre-existing rows with empty stop_id, derive it from stop_name + employee_action
	# to prevent duplicate inserts during the migration period.
	existing_index = {}
	for row in manifest_doc.transportation_manifest_details:
		if row.stop_id:
			key = (row.employee or "", row.trip_id or "", row.stop_id, row.employee_action or "")
		else:
			# Derive stop_id from existing data for backward compatibility
			direction = "RETURN" if row.employee_action == "Dropping Off" else "OUTBOUND"
			derived_stop_id = f"{row.stop_name or ''}|{direction}"
			key = (row.employee or "", row.trip_id or "", derived_stop_id, row.employee_action or "")
		existing_index[key] = row

	seen_keys = set()

	for a_row in assignment_rows:
		direction = a_row.direction
		emps = (return_emp_map if direction == "RETURN" else emp_map).get(a_row.card_id, [])
		action = "Dropping Off" if direction == "RETURN" else "Boarding"
		stop_id_val = f"{a_row.stop_location or ''}|{direction}"

		for emp in emps:
			emp_id = emp.get("id")
			if not emp_id:
				continue

			# Parse scheduled time from ISO timestamp
			time_str = a_row.end_time if direction == "RETURN" else a_row.start_time
			if time_str and "T" in time_str:
				time_str = time_str.split("T")[1][:8]

			key = (emp_id, a_row.trip_group or "", stop_id_val, action)
			seen_keys.add(key)

			if key in existing_index:
				# UPDATE: refresh system fields, preserve manual fields
				row = existing_index[key]
				row.stop_name = a_row.stop_location or ""
				row.stop_type = "Return" if direction == "RETURN" else "Pick Up"
				row.scheduled_time = time_str
				row.trip_name = a_row.trip_name or ""
				row.employee_name = emp.get("name", "")
				# Backfill stop_id for pre-existing rows
				if not row.stop_id or row.stop_id != stop_id_val:
					row.stop_id = stop_id_val
					changed = True
				if (row.row_status or "Active") != "Active":
					row.row_status = "Active"
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
					"scheduled_time": time_str,
					"requires_reliever": 0,
					"row_status": "Active",
				})
				changed = True

	# Flag rows no longer in the plan as "Removed" (preserves data)
	for key, row in existing_index.items():
		if key not in seen_keys and (row.row_status or "Active") != "Removed":
			row.row_status = "Removed"
			changed = True

	return changed
