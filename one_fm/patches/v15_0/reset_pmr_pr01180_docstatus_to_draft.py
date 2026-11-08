import frappe

PMR = "Project Manpower Request"
NAME = "PR01180"


def execute():
	"""Set PR01180 and its child rows back to draft while it is In Process."""
	if not frappe.db.exists(PMR, {"name": NAME, "docstatus": 1, "workflow_state": "In Process"}):
		return

	frappe.db.set_value(PMR, NAME, "docstatus", 0, update_modified=False)
	for df in frappe.get_meta(PMR).get_table_fields():
		frappe.db.set_value(df.options, {"parent": NAME, "parenttype": PMR}, "docstatus", 0, update_modified=False)
