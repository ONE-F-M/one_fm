import frappe

DOCTYPE = "Request for Material"
NAME = "RFM-2026-000950"
APPROVER = "abdullah@one-fm.com"
RULE = "RFM Approver"


def execute():
	"""HD-1890138: move the open assignment on RFM-2026-000950 to its corrected approver.

	fix_rfm_2026_000950_approver set the approver but left the assignment behind: it
	handed the Assignment Rule a Document where frappe.safe_eval needs a mapping, and
	AssignmentRule.safe_eval swallows that TypeError and reports the condition as False.
	So the field moved to Abdullah while the open ToDo stayed on Ahmed, which is the half
	an approver actually sees. This finishes the job on sites that already migrated.
	"""
	if not frappe.db.exists(DOCTYPE, {"name": NAME, "docstatus": 0}):
		return

	if frappe.db.get_value(DOCTYPE, NAME, "request_for_material_approver") != APPROVER:
		return

	# Nothing to move if the only live assignment is already the approver's.
	assigned = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": DOCTYPE,
			"reference_name": NAME,
			"status": ("not in", ("Cancelled", "Closed")),
			"allocated_to": ("!=", APPROVER),
		},
		limit=1,
	)
	if not assigned:
		return

	if not frappe.db.exists("Assignment Rule", {"name": RULE, "disabled": 0}):
		return

	# Replaying the rule cancels the assignment on the old approver, raises the new one
	# and refreshes _assign, exactly as a save would. as_dict for the reason above.
	frappe.get_doc("Assignment Rule", RULE).apply_assign(frappe.get_doc(DOCTYPE, NAME).as_dict())
