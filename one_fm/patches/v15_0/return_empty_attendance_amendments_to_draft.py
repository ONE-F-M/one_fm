import frappe
from frappe import _
from frappe.desk.form import assign_to
from frappe.model.workflow import apply_workflow
from frappe.query_builder import DocType


def execute():
	"""Return Pending Approval Attendance Amendments with no attendance rows to Draft."""
	if not frappe.db.has_column("Attendance Approval", "workflow_state"):
		return

	amendment = DocType("Attendance Approval")
	item = DocType("Attendance Approval Item")
	names = (
		frappe.qb.from_(amendment)
		.left_join(item)
		.on(
			(item.parent == amendment.name)
			& (item.parenttype == "Attendance Approval")
			& (item.parentfield == "attendance_details")
		)
		.select(amendment.name)
		.where(amendment.workflow_state == "Pending Approval")
		.where(item.name.isnull())
	).run(pluck=True)

	for name in names:
		doc = apply_workflow(frappe.get_doc("Attendance Approval", name), "Return To Draft")
		# Assignment rules are skipped inside patches, so move the assignment by hand.
		assign_to.close_all_assignments(doc.doctype, doc.name, ignore_permissions=True)
		assign_to.add(
			{
				"assign_to": [doc.site_supervisor_user or doc.owner],
				"doctype": doc.doctype,
				"name": doc.name,
				"description": _("Attendance Details are empty. Click Fetch Attendance Record and submit for review again."),
			}
		)

	print(f"Attendance Approvals returned to Draft: {names}")
