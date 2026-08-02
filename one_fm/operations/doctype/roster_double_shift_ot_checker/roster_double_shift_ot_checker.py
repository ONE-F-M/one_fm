# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_first_day_of_week, get_last_day_of_week, getdate, nowdate

from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor


class RosterDoubleShiftOTChecker(Document):
	pass


def get_check_periods(from_date=None):
	"""
	Return the current and next calendar week as (start_date, end_date) tuples.

	Calendar weeks (rather than rolling 7-day windows from today) keep the period label
	stable for the whole week, which is what lets repeat_count grow each day the same
	discrepancy is still unresolved.
	"""
	date = getdate(from_date or nowdate())
	current_week_start = get_first_day_of_week(date)
	next_week_start = add_days(current_week_start, 7)

	return [
		(current_week_start, get_last_day_of_week(date)),
		(next_week_start, get_last_day_of_week(next_week_start)),
	]


def format_monthweek(start_date, end_date):
	"""Period label matching the Roster Day Off Checker convention, e.g. "Jul 20 - Jul 26"."""
	return f"{getdate(start_date):%b %d} - {getdate(end_date):%b %d}"


def build_double_shift_ot_dates(schedules):
	"""One line per offending schedule: the date and the shift it was rostered on."""
	return "\n".join(f"{getdate(schedule.date)} ({schedule.shift})" for schedule in schedules)


def build_double_shift_ot_explanation(schedules):
	"""Kept short: double_shift_ot_explanation is a Data field (140 characters)."""
	shifts = {schedule.shift for schedule in schedules}
	return (
		f"{len(schedules)} Over-Time schedule(s) on {len(shifts)} shift(s) that do not allow "
		"Double Shift OT. Remove them or enable it on the shift."
	)


def get_disallowed_ot_schedules(start_date, end_date):
	"""
	Over-Time Employee Schedules rostered on shifts that do not allow Double Shift OT,
	grouped by employee.

	The roster blocks these at creation time (see extreme_schedule), so anything found
	here predates the restriction or bypassed the UI - either way a supervisor has to
	resolve it.
	"""
	EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
	OperationsShift = frappe.qb.DocType("Operations Shift")

	rows = (
		frappe.qb.from_(EmployeeSchedule)
		.join(OperationsShift)
		.on(EmployeeSchedule.shift == OperationsShift.name)
		.select(
			EmployeeSchedule.employee,
			EmployeeSchedule.date,
			EmployeeSchedule.shift,
			OperationsShift.site,
			OperationsShift.project,
		)
		.where(
			(EmployeeSchedule.roster_type == "Over-Time")
			& (EmployeeSchedule.date[start_date:end_date])
			& (OperationsShift.double_shift_ot_allowed == 0)
		)
		.orderby(EmployeeSchedule.employee)
		.orderby(EmployeeSchedule.date)
	).run(as_dict=True)

	schedules_by_employee = defaultdict(list)
	for row in rows:
		schedules_by_employee[row.employee].append(row)

	return schedules_by_employee


def create_double_shift_ot_checker(employee, monthweek, schedules, today):
	# The record is keyed on employee + week (see autoname), so the linked shift is the
	# first offending one of the week; every date/shift pair is listed in the dates field.
	# ponytail: one record per employee-week, split per shift if supervisors of different
	# shifts need to action them separately.
	shift = schedules[0].shift

	yesterday_repeat_count = frappe.db.get_value(
		"Roster Double Shift OT Checker",
		{
			"employee": employee,
			"monthweek": monthweek,
			"date": add_days(today, -1),
			"creation": ["between", [add_days(nowdate(), -1), nowdate()]],
		},
		["repeat_count"],
	)

	# Replace any existing record for this employee/week so the details reflect the latest
	# roster state instead of stacking one record per run.
	frappe.delete_doc_if_exists(
		"Roster Double Shift OT Checker", f"OPR-RDSOTC-{employee}-{monthweek}"
	)

	checker = frappe.new_doc("Roster Double Shift OT Checker")
	checker.employee = employee
	checker.date = today
	checker.monthweek = monthweek
	checker.status = "Pending"
	checker.repeat_count = (yesterday_repeat_count or 0) + 1
	checker.operations_shift = shift
	checker.shift_supervisor = get_shift_supervisor(shift)
	checker.site_supervisor = frappe.db.get_value(
		"Operations Site", schedules[0].site, "site_supervisor"
	)
	checker.project_manager = frappe.db.get_value("Project", schedules[0].project, "project_manager")
	checker.double_shift_ot_dates = build_double_shift_ot_dates(schedules)
	checker.double_shift_ot_explanation = build_double_shift_ot_explanation(schedules)
	checker.insert(ignore_permissions=True)


def check_roster_double_shift_ot():
	"""
	Flag employees rostered on a second (Over-Time) shift whose Operations Shift does not
	have "Double Shift OT Allowed" enabled, for the current and next calendar week.
	"""
	try:
		today = getdate()

		for start_date, end_date in get_check_periods(today):
			monthweek = format_monthweek(start_date, end_date)

			for employee, schedules in get_disallowed_ot_schedules(start_date, end_date).items():
				create_double_shift_ot_checker(employee, monthweek, schedules, today)

		frappe.db.commit()

	except Exception:
		frappe.log_error(
			title="Error creating double shift OT checkers", message=frappe.get_traceback()
		)


@frappe.whitelist()
def generate_checker():
	frappe.only_for(["Operations Manager", "System Manager"])
	frappe.enqueue(check_roster_double_shift_ot, queue="long", timeout=4000)
