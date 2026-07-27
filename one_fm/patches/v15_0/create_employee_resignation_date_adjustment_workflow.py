import frappe


def execute():
	"""Employee Resignation Date Adjustment never had a Workflow attached --
	workflow_state was a plain, read-only Data field nobody could actually
	change through the desk UI, and no code path ever set it to "Approved".
	This creates a real Workflow matching Employee Resignation's own pattern
	exactly:

	  Corporate (is_corporate=1): Line Manager approves directly.
	    Pending Supervisor -> Approved. No Operations Manager step at all.

	  Shift worker (is_corporate=0): forwarded to Operations Manager.
	    Pending Supervisor -> Pending Operations Manager -> Approved.

	Employee-role transitions carry allowed_user_field="supervisor",
	matching Employee Resignation Withdrawal's access-control model exactly
	-- only the specific Line Manager/Supervisor recorded on the document
	can act, not just any Employee-role user.

	Additive-only and safe to re-run: does nothing if a Workflow already
	exists for this doctype.
	"""
	workflow_name = "Employee Resignation Date Adjustment"
	if frappe.db.exists("Workflow", workflow_name):
		return

	frappe.get_doc({
		"doctype": "Workflow",
		"workflow_name": workflow_name,
		"document_type": workflow_name,
		"is_active": 1,
		"workflow_state_field": "workflow_state",
		"states": [
			{
				"state": "Pending Supervisor",
				"doc_status": "0",
				"allow_edit": "Employee",
				"style": "Warning",
			},
			{
				"state": "Pending Operations Manager",
				"doc_status": "0",
				"allow_edit": "Operations Manager",
				"style": "Warning",
			},
			{
				"state": "Approved",
				"doc_status": "1",
				"allow_edit": "Offboarding Officer",
				"style": "Success",
			},
		],
		"transitions": [
			{
				"state": "Pending Supervisor",
				"action": "Approve",
				"next_state": "Approved",
				"allowed": "Employee",
				"allowed_user_field": "supervisor",
				"condition": "doc.is_corporate",
			},
			{
				"state": "Pending Supervisor",
				"action": "Submit for Approval",
				"next_state": "Pending Operations Manager",
				"allowed": "Employee",
				"allowed_user_field": "supervisor",
				"condition": "not doc.is_corporate",
			},
			{
				"state": "Pending Operations Manager",
				"action": "Approve",
				"next_state": "Approved",
				"allowed": "Operations Manager",
			},
		],
	}).insert()

	frappe.clear_cache(doctype=workflow_name)
