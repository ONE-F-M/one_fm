import frappe

# Data repair for the recurring "Day Off / Client Day Off still linked to a Client
# Event" conflict (same root cause as fix_nirmala_day_off_client_event_conflict, but
# that patch only repaired one employee).
#
# Root cause: the roster "day off" write paths (Desk roster page + mobile/flutter)
# set employee_availability to "Day Off"/"Client Day Off" via direct SQL and never
# cleared the Client Event linkage (client_event, reference_doctype/docname,
# event_staff, event_location, is_event_schedule). A row changed from a Client Event
# to a day off therefore kept a stale event link, which the attendance job could
# treat as an event and (for plain Day Off) overwrite with "Absent".
#
# The code fix clears those fields on every write path going forward. This patch
# repairs existing data:
#   1. GENERIC: clear the stale Client Event linkage on every Day Off / Client Day Off
#      schedule row that still carries one.
#   2. TARGETED: for the reported employees, correct any conflicting "Absent"
#      attendance so it matches their day-off schedule.
#   3. Report any lingering active Shift Assignment that could re-trigger an Absent.

# Employees reported with the conflict (all linked to the same Client Event).
REPORTED_EMPLOYEES = [
	"HR-EMP-04277",  # Ishanatu Salankolay
	"HR-EMP-02800",  # Soniya Sunar
	"HR-EMP-03553",  # Jaswant Kumar Bishwakarma
	"HR-EMP-03319",  # Thillinathan Sellathambie
]

DAY_OFF_AVAILABILITIES = ["Day Off", "Client Day Off"]

STALE_LINK_FIELDS = {
	"client_event": "",
	"reference_doctype": "",
	"reference_docname": "",
	"event_staff": "",
	"event_location": "",
	"is_event_schedule": 0,
}


def execute():
	clear_stale_links()
	repair_reported_attendance()
	frappe.db.commit()


def clear_stale_links():
	"""Clear the stale Client Event linkage on all day-off schedule rows."""
	stale_rows = frappe.get_all(
		"Employee Schedule",
		filters={
			"employee_availability": ["in", DAY_OFF_AVAILABILITIES],
			"client_event": ["is", "set"],
		},
		fields=["name", "employee", "date", "employee_availability"],
	)

	for row in stale_rows:
		frappe.db.set_value(
			"Employee Schedule",
			row.name,
			STALE_LINK_FIELDS,
			update_modified=False,
		)

	print(
		f"Cleared stale Client Event linkage on {len(stale_rows)} "
		f"Day Off / Client Day Off Employee Schedule row(s)."
	)


def repair_reported_attendance():
	"""For the reported employees, fix Absent attendance that conflicts with a day off."""
	for employee in REPORTED_EMPLOYEES:
		schedules = frappe.get_all(
			"Employee Schedule",
			filters={
				"employee": employee,
				"employee_availability": ["in", DAY_OFF_AVAILABILITIES],
			},
			fields=["name", "date", "employee_availability"],
		)

		for es in schedules:
			# The correct attendance status mirrors the schedule availability.
			correct_status = es.employee_availability

			attendance = frappe.db.get_value(
				"Attendance",
				{
					"employee": employee,
					"attendance_date": es.date,
					"roster_type": "Basic",
				},
				["name", "status", "docstatus"],
				as_dict=True,
			)

			if not attendance:
				continue

			# Only correct wrong Absent marks; leave anything else untouched.
			if attendance.status == "Absent":
				comment = f"Employee Schedule - {es.name}"
				frappe.db.set_value(
					"Attendance",
					attendance.name,
					{"status": correct_status, "comment": comment},
					update_modified=False,
				)
				print(
					f"Corrected Attendance {attendance.name} for {employee} on "
					f"{es.date} from 'Absent' to '{correct_status}'."
				)

		# Report lingering active Shift Assignments that could re-trigger an Absent mark.
		lingering = frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": employee,
				"status": "Active",
				"docstatus": 1,
			},
			fields=["name", "start_date", "shift", "shift_type"],
		)
		for sa in lingering:
			# Only flag those overlapping a day-off schedule date.
			if frappe.db.exists(
				"Employee Schedule",
				{
					"employee": employee,
					"date": sa.start_date,
					"employee_availability": ["in", DAY_OFF_AVAILABILITIES],
				},
			):
				print(
					f"WARNING: Active Shift Assignment {sa.name} (shift: {sa.shift}, "
					f"type: {sa.shift_type}) exists for {employee} on {sa.start_date}, "
					f"which is a day off. Review/cancel it to avoid a re-triggered Absent."
				)
