import frappe
from frappe.utils import getdate

from one_fm.patches.v15_0.restore_wiped_ojt_employee_schedules import (
	WINDOW_END,
	WINDOW_START,
	get_approved_leave_dates,
)


def execute():
	"""Give OJT days with no attendance record at all a Shift Assignment and an
	Attendance Check for HR to decide.

	Two separate faults leave the same hole - an OJT day carrying no Attendance
	whatsoever, not even Absent:

	  * schedules deleted by the OJT fast-approval cleanup race, put back by
	    restore_wiped_ojt_employee_schedules, and
	  * schedules that survived but were written after the daily Shift Assignment cron
	    had already run for their date, so no assignment was ever created.

	Either way the employee could not check in - the app has no shift to check into -
	so the missing check-in is evidence of the bug, not of absence. Marking these Absent
	would dock pay for days the system made unattendable, so the decision is handed to a
	supervisor instead: this creates the Shift Assignment that should have existed and an
	Attendance Check in Pending Approval against it. No Attendance is written here; the
	Attendance Check workflow writes it once somebody approves.

	Scoped to the same WINDOW_START..WINDOW_END range as the restore patch that runs
	before it, so the two repair exactly the same days. The window is in the past, which
	Shift Assignment requires: it refuses a start date later than today.
	"""
	schedules = frappe.get_all(
		"Employee Schedule",
		filters={
			"roster_type": "Basic",
			"employee_availability": "On-the-job Training",
			"date": ["between", [WINDOW_START, WINDOW_END]],
		},
		fields=[
			"name", "employee", "employee_name", "date", "shift", "shift_type", "site",
			"project", "operations_role", "post_abbrv", "on_the_job_training",
		],
		order_by="date asc",
	)
	if not schedules:
		return

	assignments_created = 0
	checks_created = 0
	skipped = []

	for schedule in schedules:
		reason = skip_reason(schedule)
		if reason:
			if reason != "attendance already exists":
				skipped.append(f"{schedule.employee} {schedule.date} ({reason})")
			continue

		try:
			if create_shift_assignment(schedule):
				assignments_created += 1
			if create_attendance_check(schedule):
				checks_created += 1
			# Committed per schedule so a later failure cannot roll back work already done.
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			skipped.append(f"{schedule.employee} {schedule.date} (failed)")
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"complete_restored_ojt_attendance_chain: {schedule.name}",
			)

	frappe.log_error(
		message=(
			f"Created {assignments_created} Shift Assignment(s) and {checks_created} "
			f"Attendance Check(s) for OJT days with no attendance record.\n"
			+ (("Skipped:\n" + "\n".join(skipped)) if skipped else "Skipped: none")
		),
		title="complete_restored_ojt_attendance_chain",
	)
	frappe.db.commit()


def skip_reason(schedule):
	"""Why this schedule should be left alone, or None to go ahead.

	Anything that already has an Attendance - Present, Absent, On Leave, Day Off - is
	settled and must not be reopened; that is the ordinary case and by far the most
	common, so it is not reported as a skip.
	"""
	if frappe.db.exists(
		"Attendance",
		{
			"employee": schedule.employee,
			"attendance_date": schedule.date,
			"roster_type": "Basic",
			"docstatus": ["!=", 2],
		},
	):
		return "attendance already exists"

	if frappe.db.get_value("Employee", schedule.employee, "status") != "Active":
		return "employee not active"

	if not schedule.shift_type:
		# Without a Shift Type there are no hours to assign, and set_datetime would
		# leave the assignment without a start or end.
		return "schedule has no shift type"

	if get_approved_leave_dates(schedule.employee, getdate(schedule.date), getdate(schedule.date)):
		return "on approved leave"

	return None


def create_shift_assignment(schedule):
	"""The Shift Assignment the cron should have made for this schedule.

	Built through the ORM rather than the roster's bulk INSERT: that builder takes a
	whole day's roster and filters it by the AM/PM window it was called for, neither of
	which applies to a handful of back-dated repairs.
	"""
	if frappe.db.exists(
		"Shift Assignment",
		{
			"employee": schedule.employee,
			"start_date": schedule.date,
			"roster_type": "Basic",
			"docstatus": 1,
		},
	):
		return False

	assignment = frappe.new_doc("Shift Assignment")
	assignment.update({
		"employee": schedule.employee,
		"employee_name": schedule.employee_name,
		"company": frappe.db.get_value("Employee", schedule.employee, "company"),
		"department": frappe.db.get_value("Employee", schedule.employee, "department"),
		"start_date": schedule.date,
		"end_date": schedule.date,
		"shift_type": schedule.shift_type,
		"shift": schedule.shift,
		"site": schedule.site,
		"project": schedule.project,
		"operations_role": schedule.operations_role,
		"post_abbrv": schedule.post_abbrv,
		"roster_type": "Basic",
		"status": "Active",
		"employee_schedule": schedule.name,
		"custom_on_the_job_training": schedule.on_the_job_training,
	})
	assignment.insert(ignore_permissions=True)
	assignment.submit()

	return True


def create_attendance_check(schedule):
	"""A Pending Approval check so a supervisor decides the day, not the patch.

	Created after the Shift Assignment above so before_insert finds it and stamps the
	check with the shift and its hours.
	"""
	if frappe.db.exists(
		"Attendance Check",
		{"employee": schedule.employee, "date": schedule.date, "roster_type": "Basic"},
	):
		return False

	check = frappe.new_doc("Attendance Check")
	check.update({
		"employee": schedule.employee,
		"employee_name": schedule.employee_name,
		"date": schedule.date,
		"roster_type": "Basic",
		"workflow_state": "Pending Approval",
	})
	check.insert(ignore_permissions=True)

	return True
