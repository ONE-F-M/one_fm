import frappe
from frappe import _

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	retry_on_stale_timestamp,
)

@frappe.whitelist(methods=["POST"])
def update_manifest_row_checkin(
	row_name: str,
	attendance_status: str = None,
	qoa_status: str = None,
	qoa_reason: str = None,
	reliever_employee: str = None
):
	"""
	Updates a specific child row in Transportation Manifest Details and saves the parent manifest.
	Triggers validation and immediate persistence. Only updates fields explicitly passed in request.
	"""
	parent_manifest = frappe.db.get_value("Transportation Manifest Details", row_name, "parent")
	if not parent_manifest:
		frappe.throw(_("Child row {0} not found").format(row_name))

	# Every chip on the sheet checks in against the SAME parent manifest, so two
	# supervisors - or one supervisor tapping through a camp faster than the manifest
	# saves - open the document twice and the second save is rejected for holding a
	# stale `modified`. The row being written is the only thing this call changes, so
	# replaying it against the freshly-read manifest is safe (WI-002538).
	return retry_on_stale_timestamp(
		lambda: _apply_row_checkin(
			parent_manifest, row_name, attendance_status, qoa_status,
			qoa_reason, reliever_employee,
		)
	)


def _apply_row_checkin(parent_manifest, row_name, attendance_status, qoa_status,
					   qoa_reason, reliever_employee):
	"""Read the manifest, stamp the one row, save. Re-runnable on a save conflict."""
	doc = frappe.get_doc("Transportation Manifest", parent_manifest)
	doc.check_permission("write")

	found = False
	for row in doc.transportation_manifest_details:
		if row.name == row_name:
			# Check which fields were explicitly sent in the form request
			# This preserves fields (e.g. reliever) when saving other fields (e.g. attendance/QOA)
			if "attendance_status" in frappe.form_dict:
				row.attendance_status = attendance_status or None
				
			if "qoa_status" in frappe.form_dict:
				row.qoa_status = qoa_status or None
				
			if "qoa_reason" in frappe.form_dict:
				row.qoa_reason = qoa_reason or None
			
			if "reliever_employee" in frappe.form_dict:
				reliever = reliever_employee or None
				row.reliever_employee = reliever
				if reliever:
					# Validate that the selected reliever is Active
					status = frappe.db.get_value("Employee", reliever, "status")
					if status != "Active":
						frappe.throw(
							_("Employee {emp} cannot be selected as a reliever because they are not active").format(
								emp=reliever
							)
						)
					
					# Validate that reliever can only be set when attendance is Absent
					if row.attendance_status != "Absent":
						frappe.throw(
							_("A reliever employee can only be assigned if Attendance Status is set to Absent")
						)
					
					row.requires_reliever = 1
				else:
					row.requires_reliever = 0
			found = True
			break
			
	if not found:
		frappe.throw(_("Row {0} not found in manifest {1}").format(row_name, parent_manifest))
		
	doc.save()
	
	# Fetch the saved row values to return to the UI
	updated_row = next(r for r in doc.transportation_manifest_details if r.name == row_name)
	return {
		"status": "success",
		"message": _("Check-in saved successfully."),
		"row": {
			"name": updated_row.name,
			"attendance_status": updated_row.attendance_status,
			"qoa_status": updated_row.qoa_status,
			"qoa_reason": updated_row.qoa_reason,
			"requires_reliever": updated_row.requires_reliever,
			"reliever_employee": updated_row.reliever_employee,
			"operations_shift": updated_row.operations_shift,
			"operations_site": updated_row.operations_site,
			"operations_role": updated_row.operations_role,
			"project": updated_row.project,
			"start_time": str(updated_row.start_time) if updated_row.start_time else None,
			"end_time": str(updated_row.end_time) if updated_row.end_time else None,
		}
	}


# WI-002789: what a bulk check-in stamps on a row. A driver pressing this is saying the
# whole stop boarded and passed - anything else is an exception, taken one chip at a time.
PRESENT = "Present"
QOA_PASS = "Pass"


@frappe.whitelist(methods=["POST"])
def mark_manifest_rows_present(row_names) -> dict:
	"""Check in every un-checked employee at one stop, in a single save (WI-002789).

	One call rather than one per chip. Every row on a stop belongs to the same parent
	manifest, so twenty chips checked in individually is twenty reads and twenty saves of
	the same document - which is both slow at a departure and the exact shape that made
	WI-002538's stale-timestamp retry necessary in the first place.

	A row that has already been checked in is left exactly as it is. The driver is saying
	"everyone I have not marked yet is here"; overwriting an Absent they entered a moment
	ago would undo the one thing they did on purpose.
	"""
	if isinstance(row_names, str):
		row_names = frappe.parse_json(row_names)

	row_names = [name for name in (row_names or []) if name]
	if not row_names:
		return {"status": "success", "rows": []}

	parents = set(
		frappe.get_all(
			"Transportation Manifest Details",
			filters={"name": ["in", row_names]},
			pluck="parent",
		)
	)
	if not parents:
		frappe.throw(_("None of those rows exist on a manifest."))
	if len(parents) > 1:
		# The button acts on one stop, and a stop belongs to one manifest. More than one
		# means the caller sent rows it did not mean to.
		frappe.throw(_("Those rows belong to more than one manifest."))

	return retry_on_stale_timestamp(
		lambda: _apply_bulk_present(parents.pop(), set(row_names))
	)


def _apply_bulk_present(parent_manifest, row_names):
	"""Read the manifest, stamp every un-checked row named, save. Re-runnable."""
	doc = frappe.get_doc("Transportation Manifest", parent_manifest)
	doc.check_permission("write")

	stamped = []
	for row in doc.transportation_manifest_details:
		if row.name not in row_names or row.attendance_status:
			continue

		row.attendance_status = PRESENT
		row.qoa_status = QOA_PASS
		row.qoa_reason = None
		row.requires_reliever = 0
		stamped.append(row)

	if not stamped:
		# Everybody at the stop was already checked in. Nothing to save, and saying so is
		# better than a save that changes nothing.
		return {"status": "success", "rows": []}

	doc.save()

	return {
		"status": "success",
		"message": _("{0} employees marked present.").format(len(stamped)),
		"rows": [
			{
				"name": row.name,
				"attendance_status": row.attendance_status,
				"qoa_status": row.qoa_status,
				"qoa_reason": row.qoa_reason,
				"requires_reliever": row.requires_reliever,
			}
			for row in stamped
		],
	}
