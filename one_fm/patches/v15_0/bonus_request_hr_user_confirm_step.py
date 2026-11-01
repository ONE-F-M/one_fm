import frappe
from frappe.permissions import add_permission, update_permission_property

# The Bonus Lifecycle process adds an HR User confirmation after payroll, and the
# Payroll Operator's Cancel cancels the submitted request.


def execute():
	if not frappe.db.exists("Workflow State", "Pending HR User"):
		frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": "Pending HR User", "style": "Warning"}).insert(
			ignore_permissions=True
		)

	add_permission("Bonus Request", "HR User", 0)
	for ptype in ("read", "write"):
		update_permission_property("Bonus Request", "HR User", 0, ptype, 1, validate=False)
	update_permission_property("Bonus Request", "Payroll Operator", 0, "cancel", 1, validate=False)

	frappe.clear_cache(doctype="Bonus Request")
