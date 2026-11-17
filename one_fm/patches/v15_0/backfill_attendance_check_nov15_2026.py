# one_fm/patches/v15_0/backfill_attendance_check_nov15_2026.py
import frappe
from frappe.utils import getdate

ATTENDANCE_DATES = ("2026-11-15", "2026-11-16")


def execute():
	"""HD-1933504: generate the Attendance Check records for 15 November 2026.

	The daily generator, schedule_attendance_check on cron 15 13 * * *, is not
	registered in hooks.py. It is owned by Process Task P-TASK-2025-00001, which
	creates a Scheduled Job Type for it, and frappe's clear_events() deletes that
	job on every bench migrate because its method is not in hooks. The one_fm
	after_migrate hook update_scheduled_job_type_from_process_task recreates it
	with last_execution empty, and ScheduledJobType.get_next_execution() then
	falls back to creation, so the next run is computed from the moment of the
	migrate.

	On 16 November a deploy held the scheduler from 13:05 to 13:57 and the job
	was recreated at 13:47 with last_execution empty, which pushed its next run
	to 17 November 13:15. The 13:15 slot of 16 November never fired, and
	create_attendance_check() only ever covers "yesterday", so 15 November can
	never regenerate itself.

	16 November is included because deploying this patch is itself a migrate: if
	it lands across today's 13:15 slot, that day would be lost the same way. A
	date that already has records is skipped, so only the genuinely missing days
	are created.

	It calls the generator's internals rather than create_attendance_check()
	because that entry point is wrapped in production_domain() and would be a
	silent no-op for a developer running it locally.

	Safe to run anywhere and more than once:
	  * missing table or missing generator code, it reports and returns
	  * records already present for a date, it reports and skips that date
	  * no source data for a date (any dev or fresh site), it reports and skips it
	  * duplicates are rejected by AttendanceCheck.validate_duplicate() and
	    swallowed by insert_attendance_check_records()
	It never raises, so a migrate cannot be blocked by it.
	"""
	if not frappe.db.table_exists("Attendance Check"):
		print("Attendance Check backfill: skipped, the Attendance Check table does not exist")
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
		print("Attendance Check backfill: skipped, the generator functions are not available")
		return

	for attendance_date in ATTENDANCE_DATES:
		_backfill_one_date(
			getdate(attendance_date),
			get_absentees_on_date,
			get_attendance_not_marked_shift_employees,
			insert_attendance_check_records,
		)


def _backfill_one_date(
	date,
	get_absentees_on_date,
	get_attendance_not_marked_shift_employees,
	insert_attendance_check_records,
):
	existing = frappe.db.count("Attendance Check", {"date": date})
	if existing:
		print(f"Attendance Check backfill {date}: skipped, {existing} record(s) already exist for the date")
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
