import frappe

DOCTYPE = "Request for Material"
STATE = "Pending Approval"
NAMES = ("RFM-2026-001001", "RFM-2026-001017")
RELIEVER = "a.alazmi@one-fm.com"
ON_LEAVE = "m.mothaffar@one-fm.com"
RULE = "RFM Approver"


def execute():
	"""HD-1910279: hand RFM-2026-001001 and RFM-2026-001017 to the reliever.

	Both requests were raised while Mohammad H Mothaffar was on Annual Leave
	(HR-LAP-2026-01362, 28 Oct - 07 Nov) with Ali Mohammad Alshabo as his reliever, and
	both still name Mothaffar as request_for_material_approver. Approval is gated on
	that field matching the session user - before_workflow_action throws "You are not
	authorized to approve!!" for anyone else - so the reliever can open them and do
	nothing with them.

	The Reliever Assignment handover could not move the field: it rewrites document
	fields only for the doctypes listed in Reliever Assignment Settings, and it runs
	once, at handover, which both of these predate. This corrects the two documents;
	the general case is for the Reliever Assignment to handle.

	Only the approver is touched, and only while the request is still unapproved and
	still in Pending Approval - a request someone has already decided keeps the trail it
	was decided on.
	"""
	if not frappe.db.exists("User", {"name": RELIEVER, "enabled": 1}):
		return

	for name in NAMES:
		if not frappe.db.exists(
			DOCTYPE,
			{
				"name": name,
				"docstatus": 0,
				"workflow_state": STATE,
				"request_for_material_approver": ON_LEAVE,
			},
		):
			continue

		frappe.db.set_value(DOCTYPE, name, "request_for_material_approver", RELIEVER, update_modified=False)

		# The ToDo is what the approver actually sees, so the assignment has to follow
		# the field. Replaying the rule cancels the assignment on the employee who is
		# away and raises the reliever's, exactly as a save would.
		if frappe.db.exists("Assignment Rule", {"name": RULE, "disabled": 0}):
			# as_dict, not the Document: the rule evaluates assign_condition through
			# frappe.safe_eval, whose eval_locals has to be a mapping. A Document is not
			# one, and the TypeError is swallowed inside AssignmentRule.safe_eval, so the
			# rule quietly decides the condition is False and assigns nobody.
			frappe.get_doc("Assignment Rule", RULE).apply_assign(frappe.get_doc(DOCTYPE, name).as_dict())

	frappe.db.commit()
