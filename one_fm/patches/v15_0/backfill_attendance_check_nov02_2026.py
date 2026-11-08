# one_fm/patches/v15_0/backfill_attendance_check_nov02_2026.py
import frappe
from frappe.utils import getdate

ATTENDANCE_DATE = "2026-11-02"


def execute():
	"""HD-1914594: generate the Attendance Check records for 2 November 2026.

	The daily job (schedule_attendance_check, cron 15 13 * * *) fired on
	3 November but the long-queue job it enqueues never inserted anything, and
	create_attendance_check() only ever covers "yesterday", so the day can never
	regenerate itself. This patch does that one day.

	It calls the generator's internals rather than create_attendance_check()
	because that entry point is wrapped in production_domain() and would be a
	silent no-op for a developer running it locally.

	Safe to run anywhere and more than once:
	  * missing table or missing generator code, it reports and returns
	  * records already present for the date, it reports and returns
	  * no source data for the date (any dev or fresh site), it reports and returns
	  * duplicates are rejected by AttendanceCheck.validate_duplicate() and
	    swallowed by insert_attendance_check_records()
	It never raises, so a migrate cannot be blocked by it.
	"""
	date = getdate(ATTENDANCE_DATE)

	if not frappe.db.table_exists("Attendance Check"):
		print(f"Attendance Check backfill {date}: skipped, the Attendance Check table does not exist")
		return

	existing = frappe.db.count("Attendance Check", {"date": date})
	if existing:
		print(f"Attendance Check backfill {date}: skipped, {existing} record(s) already exist for the date")
		return

	try:
		from one_fm.one_fm.doctype.attendance_check.attendance_check import (
			get_absentees_on_date,
			get_attendance_not_marked_shift_employees,
			insert_attendance_check_records,
		)
	except ImportError:
		frappe.log_error(
			title="Attendance Check Backfill",
			message=frappe.get_traceback(),
		)
		print(f"Attendance Check backfill {date}: skipped, the generator functions are not available")
		return

	try:
		details = _collect_details(
			date, get_absentees_on_date, get_attendance_not_marked_shift_employees
		)
	except Exception:
		frappe.log_error(
			title="Attendance Check Backfill",
			message=frappe.get_traceback(),
		)
		print(f"Attendance Check backfill {date}: skipped, the source queries failed, see the Error Log")
		return

	if not details:
		print(f"Attendance Check backfill {date}: nothing to do, no absentees and no unmarked shift assignments")
		return

	print(f"Attendance Check backfill {date}: creating checks for {len(details)} employee(s)")

	try:
		insert_attendance_check_records(details, date)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			title="Attendance Check Backfill",
			message=frappe.get_traceback(),
		)
		print(f"Attendance Check backfill {date}: failed, see the Error Log")
		return

	created = frappe.db.count("Attendance Check", {"date": date})
	print(f"Attendance Check backfill {date}: done, {created} record(s) now exist for the date")


def _collect_details(date, get_absentees_on_date, get_attendance_not_marked_shift_employees):
	"""Both generator sources for the date, de-duplicated on employee and roster type.

	Each source can be empty, and the two never normally overlap (an absentee has
	an Attendance record, which is what the second query looks for the absence of),
	but the second one can repeat an employee who holds more than one Shift
	Assignment covering the date.
	"""
	details = []
	seen = set()

	for source in (
		get_absentees_on_date(date) or [],
		get_attendance_not_marked_shift_employees(date) or [],
	):
		for data in source:
			employee = data.get("employee")
			if not employee:
				continue
			key = (employee, data.get("roster_type") or "Basic")
			if key in seen:
				continue
			seen.add(key)
			details.append(data)

	return details
