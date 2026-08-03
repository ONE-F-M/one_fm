import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.attendance import get_attendance_custom_fields


def execute():
	"""Put Event Staff on Attendance, and fill it in for the records already there
	(WI-001686).

	The field is what makes Attendance a Connection on Event Staff. Custom fields are
	only created by the installer, so an existing site needs it created here.

	`fetch_from` populates on save, which no historical attendance is going to get, so
	the Connection would read zero on every event that has already happened. The
	backfill reads the same hop the field does - the Shift Assignment's Event Staff -
	and skips anything already set.
	"""
	create_custom_fields(get_attendance_custom_fields(), update=True)

	# Attendance -> Shift Assignment -> Event Staff, for rows that have not got there yet.
	assignments = {
		row.name: row.event_staff
		for row in frappe.get_all(
			"Shift Assignment",
			filters={"event_staff": ["is", "set"]},
			fields=["name", "event_staff"],
		)
	}
	if not assignments:
		return

	attendance = frappe.get_all(
		"Attendance",
		filters={
			"shift_assignment": ["in", list(assignments)],
			"custom_event_staff": ["is", "not set"],
		},
		fields=["name", "shift_assignment"],
	)
	if not attendance:
		return

	# Grouped so this is one update per event staff record rather than per attendance.
	by_event_staff = {}
	for row in attendance:
		by_event_staff.setdefault(assignments[row.shift_assignment], []).append(row.name)

	for event_staff, names in by_event_staff.items():
		frappe.db.set_value(
			"Attendance",
			{"name": ["in", names]},
			"custom_event_staff",
			event_staff,
			update_modified=False,
		)

	frappe.db.commit()
	print(
		f"WI-001686: set Event Staff on {len(attendance)} attendance record(s) "
		f"across {len(by_event_staff)} event staff record(s)"
	)
