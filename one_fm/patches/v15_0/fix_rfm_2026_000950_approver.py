import frappe

DOCTYPE = "Request for Material"
NAME = "RFM-2026-000950"
APPROVER = "abdullah@one-fm.com"
RULE = "RFM Approver"


def execute():
	"""HD-1890138: point RFM-2026-000950 back at the approver the requester chose.

	The request is for Abdullah, who has no Reports To because he is the top of the
	chain, so get_request_for_material_approver fell through to the Site Supervisor of
	his Allocated Site and set Ahmed Abdelmenim. The controller now recognises a super
	user, but the document was already saved and assigned, so this one corrects it.

	Only the approver field is touched, and only while the request is still unapproved -
	a request someone has already acted on keeps the trail it was decided on.
	"""
	if not frappe.db.exists(DOCTYPE, {"name": NAME, "docstatus": 0}):
		return

	if frappe.db.get_value(DOCTYPE, NAME, "request_for_material_approver") == APPROVER:
		return

	if not frappe.db.exists("User", APPROVER):
		return

	frappe.db.set_value(DOCTYPE, NAME, "request_for_material_approver", APPROVER, update_modified=False)

	# The ToDo is what the approver actually sees, so the assignment has to follow the
	# field. Replaying the rule clears the assignment on the old approver and raises the
	# new one exactly as a save would have.
	if frappe.db.exists("Assignment Rule", {"name": RULE, "disabled": 0}):
		frappe.get_doc("Assignment Rule", RULE).apply_assign(frappe.get_doc(DOCTYPE, NAME))
