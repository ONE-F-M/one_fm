import frappe
from frappe.utils import flt, get_datetime


DATE = "2026-07-13"


def execute():
	"""Backfill Present Attendance for auto-attendance employees whose IN check-in
	was never generated on 2026-07-13.

	Root cause: the hourly `auto_generate_checkin` job dropped the morning IN batch
	on 2026-07-13, so 48 auto-attendance employees got only an OUT check-in and no
	Attendance record was ever created — which correctly (but undesirably) raised an
	Attendance Check for each. Their Shift Assignments existed and they worked a normal
	08:00-17:00 shift, so this patch marks them Present for that day.

	Idempotent: skips any employee who already has a non-cancelled Basic Attendance
	for the date.
	"""

	# Target set: employees flagged by an Attendance Check on the date, who are
	# auto-attendance, who still have no Attendance for the day, and who had an
	# active Shift Assignment on the date.
	flagged_employees = frappe.get_all(
		"Attendance Check",
		filters={"date": DATE},
		pluck="employee",
	)
	flagged_employees = list(set(flagged_employees))

	created_count = 0
	skipped_count = 0
	failed_count = 0

	for employee in flagged_employees:
		try:
			# Must be an auto-attendance employee.
			if not frappe.db.get_value("Employee", employee, "auto_attendance"):
				continue

			# Idempotency: skip if a non-cancelled Basic Attendance already exists.
			if frappe.db.exists(
				"Attendance",
				{
					"employee": employee,
					"attendance_date": DATE,
					"roster_type": "Basic",
					"docstatus": ["<", 2],
				},
			):
				skipped_count += 1
				continue

			# Must have an active, submitted Shift Assignment for the date.
			shift_assignment = frappe.db.get_value(
				"Shift Assignment",
				{
					"employee": employee,
					"start_date": DATE,
					"status": "Active",
					"roster_type": "Basic",
					"docstatus": 1,
				},
				[
					"name",
					"company",
					"department",
					"shift_type",
					"shift",
					"site",
					"start_datetime",
					"end_datetime",
				],
				as_dict=True,
			)
			if not shift_assignment:
				continue

			# Working hours from the scheduled shift window (08:00-17:00 -> 9 hours).
			working_hours = 0.0
			if shift_assignment.start_datetime and shift_assignment.end_datetime:
				delta = get_datetime(shift_assignment.end_datetime) - get_datetime(
					shift_assignment.start_datetime
				)
				working_hours = flt(delta.total_seconds() / 3600.0, 2)
			if working_hours <= 0:
				# Present requires working_hours > 0; skip if the window is unusable.
				failed_count += 1
				frappe.log_error(
					message=f"Could not derive working hours for {employee} on {DATE}",
					title="Backfill Present Attendance Jul13",
				)
				continue

			attendance = frappe.new_doc("Attendance")
			attendance.employee = employee
			attendance.attendance_date = DATE
			attendance.status = "Present"
			attendance.roster_type = "Basic"
			attendance.company = shift_assignment.company
			attendance.department = shift_assignment.department
			# SA.shift_type is the Shift Type link; SA.shift is the Operations Shift.
			attendance.shift = shift_assignment.shift_type
			attendance.operations_shift = shift_assignment.shift
			attendance.site = shift_assignment.site
			attendance.shift_assignment = shift_assignment.name
			attendance.working_hours = working_hours

			attendance.flags.ignore_permissions = True
			attendance.insert(ignore_permissions=True)
			attendance.submit()

			created_count += 1
			frappe.db.commit()

		except Exception as e:
			failed_count += 1
			frappe.db.rollback()
			frappe.log_error(
				message=f"Error marking Present for {employee} on {DATE}: {str(e)}\n{frappe.get_traceback()}",
				title="Backfill Present Attendance Jul13",
			)

	print(
		f"Backfill Present Attendance {DATE}: created {created_count}, "
		f"skipped (already marked) {skipped_count}, failed {failed_count}."
	)
