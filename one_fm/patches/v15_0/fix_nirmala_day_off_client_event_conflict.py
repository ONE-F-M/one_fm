import frappe

# One-time data repair for HR-EMP-03989 (Nirmala Neupane) on 2026-06-15.
#
# Her roster for that date was changed from "Client Event" to "Day Off" via the
# roster's dayoff() action, which (before the fix in roster.py) wrote the schedule
# row with raw SQL and failed to clear the Client Event reference fields. This left
# the Employee Schedule showing "Day Off" while still linked to the old Client Event,
# which caused the hourly attendance job to overwrite her "Day Off" with "Absent".
#
# This patch:
#   1. Clears the stale Client Event linkage on the Day Off schedule row.
#   2. Detects (and reports) any lingering active Shift Assignment for that date that
#      would re-trigger an Absent mark, so it can be reviewed/cancelled separately.
#   3. Removes the wrong Absent attendance and re-marks the date as Day Off.

EMPLOYEE = "HR-EMP-03989"
DATE = "2026-06-15"


def execute():
	schedules = frappe.get_all(
		"Employee Schedule",
		filters={"employee": EMPLOYEE, "date": DATE},
		fields=["name", "employee_availability", "client_event", "roster_type"],
	)

	if not schedules:
		print(f"No Employee Schedule found for {EMPLOYEE} on {DATE}; nothing to repair.")
		return
	for es in schedules:
		# Only repair day-off rows that still carry a Client Event link (the conflict).
		if es.employee_availability in ("Day Off", "Client Day Off") and es.client_event:
			frappe.db.set_value(
				"Employee Schedule",
				es.name,
				{
					"client_event": "",
					"reference_doctype": "",
					"reference_docname": "",
					"event_staff": "",
					"event_location": "",
					"is_event_schedule": 0,
				},
				update_modified=False,
			)
			print(f"Cleared stale Client Event linkage on Employee Schedule {es.name}.")

	# Shift Assignment check: a lingering active assignment for the date will cause the
	# hourly job to re-create an Absent record. Report it for manual review.
	lingering = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": EMPLOYEE,
			"start_date": DATE,
			"status": "Active",
			"docstatus": 1,
		},
		fields=["name", "shift_type", "shift"],
	)
	for sa in lingering:
		print(
			f"WARNING: Active Shift Assignment {sa.name} (shift: {sa.shift}, "
			f"type: {sa.shift_type}) still exists for {EMPLOYEE} on {DATE}. "
			f"This may re-trigger an Absent mark and should be reviewed/cancelled."
		)

	# Remove the wrong Absent attendance for the Basic roster, then re-mark Day Off.
	frappe.db.delete(
		"Attendance",
		{
			"employee": EMPLOYEE,
			"attendance_date": DATE,
			"roster_type": "Basic",
			"status": "Absent",
		},
	)
	frappe.db.commit()

	# Re-run the standard single-attendance marker, which honours the Day Off schedule.
	from one_fm.overrides.attendance import mark_single_attendance

	# mark_single_attendance -> mark_for_shift_assignment calls att_date.date(),
	# so it needs a datetime, not the bare "YYYY-MM-DD" string.
	mark_single_attendance(EMPLOYEE, frappe.utils.get_datetime(DATE), roster_type="Basic")
	frappe.db.commit()

	att = frappe.db.get_value(
		"Attendance",
		{"employee": EMPLOYEE, "attendance_date": DATE, "roster_type": "Basic"},
		["name", "status"],
		as_dict=True,
	)
	if att:
		print(f"Attendance {att.name} for {EMPLOYEE} on {DATE} is now '{att.status}'.")
	else:
		print(f"No attendance present for {EMPLOYEE} on {DATE} after re-marking.")
