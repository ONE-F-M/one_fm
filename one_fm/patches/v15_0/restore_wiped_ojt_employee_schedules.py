import frappe
from frappe.utils import add_days, getdate


# The repair is deliberately confined to the reported window rather than to every day
# the cleanup race could have touched. Older gaps are left for a decision of their own:
# rebuilding a month of roster history as a side effect of fixing four days would change
# far more than was asked for.
WINDOW_START = "2026-09-08"
WINDOW_END = "2026-09-11"


def execute():
	"""Rebuild Employee Schedules wiped by the OJT fast-approval cleanup race.

	An OJT used to enqueue "delete this OJT's roster entries" the moment it was
	created. For a request approved within a couple of minutes, that job ran *after*
	approval had already written the daily Employee Schedules and removed them again,
	leaving a hole in the roster - and with no schedule there is no Shift Assignment,
	no check-in and no Attendance for those days.

	The race itself is fixed (cleanup now only runs on Draft/Rejected), but the rows
	already deleted never came back. This fills them in.

	Scoped to WINDOW_START..WINDOW_END, the reported range. Only the part of an OJT that
	falls inside that window is considered, so a training spanning it is repaired for
	those days and left alone either side.

	Strictly additive: a date is only rebuilt when the employee has *no* Basic
	Employee Schedule for it and is not on approved leave. Anything already on the
	roster - a later OJT, a Day Off, a normal shift - is left exactly as it is, so a
	hole that was since filled by hand is not overwritten.

	Schedules only. Turning a restored day into an attendance record is
	complete_restored_ojt_attendance_chain, which runs next and hands the decision to a
	supervisor rather than writing Attendance itself.
	"""
	ojts = frappe.get_all(
		"On the Job Training",
		filters={
			"docstatus": 1,
			"workflow_state": "Approved",
			"start_date": ["<=", WINDOW_END],
			"end_date": [">=", WINDOW_START],
		},
		fields=["name", "employee", "start_date", "end_date"],
		order_by="start_date asc",
	)
	if not ojts:
		return

	restored = 0
	skipped = []

	for ojt in ojts:
		if not ojt.start_date:
			continue

		# Employee Schedule refuses a non-active employee, and rightly so - somebody who
		# has since left should not be put back on the roster to fix a historical gap.
		if frappe.db.get_value("Employee", ojt.employee, "status") != "Active":
			skipped.append(f"{ojt.name} {ojt.employee} (employee not active)")
			continue

		missing = get_missing_schedule_dates(ojt)
		if not missing:
			continue

		ojt_doc = frappe.get_doc("On the Job Training", ojt.name)

		for schedule_date in missing:
			try:
				create_schedule(ojt_doc, schedule_date)
				# Committed per row so a later failure cannot roll back work already done.
				frappe.db.commit()
				restored += 1
			except Exception:
				frappe.db.rollback()
				skipped.append(f"{ojt.name} {ojt.employee} {schedule_date}")
				continue

	frappe.log_error(
		message=(
			f"Rebuilt {restored} Employee Schedule(s) wiped by the OJT cleanup race.\n"
			+ (("Skipped:\n" + "\n".join(skipped)) if skipped else "Skipped: none")
		),
		title="restore_wiped_ojt_employee_schedules",
	)
	frappe.db.commit()


def get_missing_schedule_dates(ojt):
	"""Dates inside the OJT range *and* the repair window where the employee should be
	rostered but is not.

	A date is missing only when it carries no Basic Employee Schedule *and* the
	employee is not on approved leave. Leave taken during a training is real - one of
	the affected employees was on approved Sick Leave for three of the wiped days - and
	putting a training day back on top of it would overstate the roster rather than
	repair it.
	"""
	# Clamped to the window: an OJT running past it keeps whatever the roster says for
	# the days outside, repaired or not.
	start_date = max(getdate(ojt.start_date), getdate(WINDOW_START))
	end_date = min(getdate(ojt.end_date) if ojt.end_date else getdate(ojt.start_date), getdate(WINDOW_END))
	if end_date < start_date:
		return []

	existing = {
		getdate(row.date)
		for row in frappe.get_all(
			"Employee Schedule",
			filters={
				"employee": ojt.employee,
				"roster_type": "Basic",
				"date": ["between", [start_date, end_date]],
			},
			fields=["date"],
		)
	}

	on_leave = get_approved_leave_dates(ojt.employee, start_date, end_date)

	missing = []
	current_date = start_date
	while current_date <= end_date:
		if current_date not in existing and current_date not in on_leave:
			missing.append(current_date)
		current_date = add_days(current_date, 1)

	return missing


def get_approved_leave_dates(employee, start_date, end_date):
	"""Every date in the window covered by a submitted, approved Leave Application."""
	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
		},
		fields=["from_date", "to_date"],
	)

	dates = set()
	for leave in leaves:
		current_date = max(getdate(leave.from_date), start_date)
		leave_end = min(getdate(leave.to_date), end_date)
		while current_date <= leave_end:
			dates.add(current_date)
			current_date = add_days(current_date, 1)

	return dates


def create_schedule(ojt_doc, schedule_date):
	"""Insert the one schedule the OJT would have created for this date.

	Field mapping is taken from the OJT controller itself rather than copied here, so
	a rebuilt row is identical to one the OJT writes normally.
	"""
	schedule_doc = frappe.new_doc("Employee Schedule")
	schedule_doc.employee = ojt_doc.employee
	schedule_doc.date = schedule_date
	schedule_doc.roster_type = "Basic"

	ojt_doc.update_employee_schedule_fields(schedule_doc, schedule_date)

	schedule_doc.insert(ignore_permissions=True)
