import frappe
from frappe import _

@frappe.whitelist()
def update_manifest_row_checkin(row_name, attendance_status=None, qoa_status=None, qoa_reason=None, reliever_employee=None):
	"""
	Updates a specific child row in Transportation Manifest Details and saves the parent manifest.
	Triggers validation and immediate persistence.
	"""
	parent_manifest = frappe.db.get_value("Transportation Manifest Details", row_name, "parent")
	if not parent_manifest:
		frappe.throw(_("Child row {0} not found").format(row_name))
		
	doc = frappe.get_doc("Transportation Manifest", parent_manifest)
	doc.check_permission("write")
	
	found = False
	for row in doc.transportation_manifest_details:
		if row.name == row_name:
			row.attendance_status = attendance_status or None
			row.qoa_status = qoa_status or None
			row.qoa_reason = qoa_reason or None
			row.reliever_employee = reliever_employee or None
			if reliever_employee:
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
		}
	}
