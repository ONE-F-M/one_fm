import frappe


def execute():
	"""Remove the approvers' Request Relieving Date Change from the stored Employee Resignation workflow.
	Only those transitions go, so resignations already sent back can still be resubmitted."""
	if not frappe.db.exists("Workflow", "Employee Resignation"):
		return

	workflow = frappe.get_doc("Workflow", "Employee Resignation")
	workflow.transitions = [t for t in workflow.transitions if t.action != "Request Relieving Date Change"]
	workflow.save()
