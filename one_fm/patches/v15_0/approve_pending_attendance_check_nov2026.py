# one_fm/patches/v15_0/approve_pending_attendance_check_nov2026.py
import frappe

ATTENDANCE_DATES = (
	"2026-11-02",
	"2026-11-05",
	"2026-11-06",
	"2026-11-07",
	"2026-11-09",
	"2026-11-10",
	"2026-11-11",
	"2026-11-12",
	"2026-11-13",
)
ATTENDANCE_STATUS = "Present"
JUSTIFICATION = "Approved by Administrator"


def execute():
	"""Approve the Attendance Checks left in "Pending Approval" for HD-1925623.

	HR (Ahmed Abdelmenim, HR Supervisor) asked on 15 November 2026 to approve
	the pending records as Present and to include 11, 12 and 13 November. The
	date list above is exactly that scope: the dates that were pending when the
	request was made, plus the three dates named. 13 November carries no pending
	record, it is listed so the scope matches the request. 14 November is
	deliberately excluded because those records were created after the request.

	Each check is set to Attendance Status "Present" with the justification
	"Approved by Administrator" and moved to the workflow state "Approved",
	which is the docstatus 1 state of the Attendance Check workflow. Submitting
	therefore runs the normal approval chain in ``on_submit``: the Employee
	Checkin backfill and the Attendance marking.

	Why the Attendance Status has to be set as well:

	* ``validate_justification`` blanks the justification for any status other
	  than "Present", so the requested justification would not survive.
	* ``on_submit`` throws "To Approve the record set Attendance Status" when
	  the field is empty, and most of these records were created with it blank.
	  The rest carry "Absent", which this patch overwrites with "Present" as
	  requested.

	Validations this deliberately relies on rather than bypasses:

	* ``validate_justification`` restricts "Approved by Administrator" to the
	  Attendance Manager via ``check_attendance_manager``, which also whitelists
	  the Administrator session that patches run under.
	* "Approved by Administrator" is not one of the justifications that require
	  a screenshot, a mobile brand/model or an "Other" reason, so no further
	  dependent field is needed.
	* ``set_action`` resolves the action to "No Action Required", so neither a
	  Penalty And Investigation nor an Attendance Check Action is spawned.

	Around 23 of the records in scope are expected to fail on downstream
	validation: an Employee Checkin cannot be created for an employee who is no
	longer Active (Left, Not Returned from Leave or on Vacation), nor for a
	check with no Shift Assignment and hence no start/end time. Each record is
	committed on its own and rolled back in isolation on failure, so one bad
	record cannot stick the whole patch. The failures are collected into a
	single Error Log so they can be handled individually, most likely by
	Attendance Request.
	"""
	names = frappe.get_all(
		"Attendance Check",
		filters={
			"date": ["in", ATTENDANCE_DATES],
			"workflow_state": "Pending Approval",
			"docstatus": 0,
		},
		pluck="name",
	)
	if not names:
		return

	# Pin the session to Administrator so the check_attendance_manager gate on
	# "Approved by Administrator" passes regardless of who triggered the migrate.
	original_user = frappe.session.user
	frappe.set_user("Administrator")

	approved = []
	failures = []

	try:
		for name in names:
			try:
				doc = frappe.get_doc("Attendance Check", name)
				doc.attendance_status = ATTENDANCE_STATUS
				doc.justification = JUSTIFICATION
				doc.workflow_state = "Approved"
				doc.flags.ignore_permissions = True
				doc.submit()
				frappe.db.commit()
				approved.append(name)
			except Exception as e:
				# Roll back only this record; everything before it is committed.
				frappe.db.rollback()
				failures.append(f"{name}: {frappe.utils.cstr(e)[:500]}")
	finally:
		frappe.set_user(original_user)

	if failures:
		frappe.log_error(
			title="Approve Pending Attendance Check Nov 2026",
			message=(
				f"Approved {len(approved)} of {len(names)} Attendance Checks.\n\n"
				f"Failed ({len(failures)}):\n" + "\n".join(failures)
			),
		)

	print(
		f"Attendance Check {ATTENDANCE_DATES[0]} to {ATTENDANCE_DATES[-1]}:"
		f" approved {len(approved)} of {len(names)}, {len(failures)} failed"
	)
