import frappe

DOCTYPE = "Absence Case"

# The nightly absence check (api/tasks.attendance_query_script) re-raised a case for the
# same absence roughly every 16 days: its consecutive-day rule searched back to 1 January
# with no "is this run still live" gate, and create_absence_case only suppressed duplicates
# created in the previous 15 days. One February absence therefore produced a fresh case in
# March, April, ... and October, each one assigned to the HR Officer (HD-1858822). The job
# is fixed; this clears the backlog those runs left behind.
#
# Measured on production on 2026-10-06: 414 active auto-raised cases, 47 of which are
# employee/type groups holding more than one copy, 311 copies to remove - every one of
# them still a Draft nobody had opened.

# Only the types the nightly job raises. A case entered by hand is never touched.
AUTO_TYPES = (
	"5 Days Consecutive Absence",
	"7 Days Consecutive Absence",
	"16 Days Absence in a Year",
	"21 Days Absence in a Year",
)

# Any of these filled in means somebody has worked the case. A worked case is kept and
# never removed, even when it is the later copy of a duplicate pair - the investigation
# recorded on it is the real work product, and which copy it landed on is an accident of
# which assignment the officer happened to open. (On production the one worked copy in
# this backlog is indeed the newest, not the oldest.)
WORK_FIELDS = (
	"location_status",
	"has_contact_been_made",
	"absence_reason_details",
	"leave_application",
	"formal_hearing_start_datetime",
	"unpaid_leave_request_decision",
)

FIELDS = [
	"name",
	"employee",
	"absence_type",
	"creation",
	"modified_by",
	"docstatus",
] + list(WORK_FIELDS)


def execute():
	if not frappe.db.table_exists(DOCTYPE):
		return

	cases = frappe.get_all(
		DOCTYPE,
		filters={"docstatus": ["<", 2], "absence_type": ["in", AUTO_TYPES]},
		fields=FIELDS,
		order_by="creation asc",
	)

	groups = {}
	for case in cases:
		groups.setdefault((case.employee, case.absence_type), []).append(case)

	removed = 0
	for group in groups.values():
		if len(group) < 2:
			continue

		for case in duplicates_to_remove(group):
			if remove_case(case):
				removed += 1

	frappe.db.commit()
	print("Removed {0} duplicate Absence Cases".format(removed))


def duplicates_to_remove(group: list) -> list:
	"""Every untouched copy in the group except the one that is kept.

	The kept case is the earliest worked one, or the earliest of all when none has been
	worked - the copy raised closest to the absence itself, which for these employees is
	the one raised days after they actually stopped coming in. Worked copies are always
	kept, so a group where several were filled in loses none of them.
	"""
	worked = [case for case in group if is_worked(case)]
	keeper = worked[0] if worked else group[0]

	return [
		case for case in group
		if case.name != keeper.name and not is_worked(case)
	]


def is_worked(case) -> bool:
	if any(case.get(field) for field in WORK_FIELDS):
		return True

	# A case the job raised and nobody opened is still owned and last-modified by
	# Administrator; anyone else in modified_by means a person has been in it.
	return case.modified_by not in (None, "Administrator")


def remove_case(case) -> bool:
	"""Delete a duplicate Draft, or cancel a duplicate that was submitted.

	Every copy in the current backlog is a Draft, and a Draft has no cancelled state to
	move to - docstatus 0 goes to 2 through no legal transition, and a document marked
	Cancelled that was never submitted reads as something that happened when nothing did.
	Deleting is what a Draft nobody opened deserves. The submitted branch exists for the
	copies a future backlog may contain; it writes the docstatus directly rather than
	calling cancel(), because validate() re-reads Attendance that is months old by then.
	"""
	try:
		if case.docstatus == 0:
			close_assignments(case.name)
			frappe.delete_doc(
				DOCTYPE,
				case.name,
				force=True,
				ignore_permissions=True,
				delete_permanently=True,
			)
		else:
			frappe.db.set_value(DOCTYPE, case.name, "docstatus", 2, update_modified=False)
			close_assignments(case.name)
			frappe.get_doc(
				{
					"doctype": "Comment",
					"comment_type": "Info",
					"reference_doctype": DOCTYPE,
					"reference_name": case.name,
					"content": (
						"Cancelled by patch cancel_duplicate_absence_cases (HD-1858822): "
						"duplicate case raised by the nightly absence check for an absence "
						"an earlier case already covers."
					),
				}
			).insert(ignore_permissions=True)

		return True
	except Exception:
		frappe.log_error(
			title="cancel_duplicate_absence_cases",
			message="Could not remove {0}\n{1}".format(case.name, frappe.get_traceback()),
		)
		return False


def close_assignments(name: str):
	"""Cancel the open ToDos pointing at a case before it goes.

	Done explicitly rather than left to the delete: these ToDos are the HR Officer's
	inbox, and an assignment surviving the case it points at is the complaint this patch
	exists to answer.
	"""
	todos = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": DOCTYPE,
			"reference_name": name,
			"status": ["!=", "Cancelled"],
		},
		pluck="name",
	)

	for todo in todos:
		frappe.db.set_value("ToDo", todo, "status", "Cancelled", update_modified=False)
