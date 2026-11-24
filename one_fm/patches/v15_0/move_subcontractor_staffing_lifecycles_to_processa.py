import frappe

from one_fm.custom.workflow.workflow import create_workflow_action_master, create_workflow_state
from one_fm.grd.processa import retire_workflow

# The Request Subcontract Staff, Subcontractor Staff Shortlist, Subcontractor Exit and
# Subcontractor Contracts processes set these states and offer these actions.
STATES = (
	("Draft", "Danger"),
	("Pending Project Manager", "Warning"),
	("Pending Operations Admin", "Warning"),
	("Pending Onboarding Officer", "Warning"),
	("Pending Operations Manager", "Warning"),
	("Pending GSD Supervisor", "Danger"),
	("Pending Offboarding Officer", "Danger"),
	("Pending Finance Manager", "Warning"),
	("Approved", "Success"),
	("Rejected", "Primary"),
	("Completed", "Success"),
	("Active", "Primary"),
	("Inactive", "Inverse"),
)
ACTIONS = (
	"Submit for Review", "Approve", "Reject", "Return to Draft", "Submit to Onboarding Officer",
	"Submit", "Complete Processing", "Set as Active", "Set Inactive",
)
RULES = {
	"Subcontract Staff Request": ("Subcontract Staff Request",),
	"Subcontract Staff Shortlist": ("Subcontract Staff Shortlist",),
	"Subcontractor Exit": (
		"Project Manager Approval",
		"Operations Manager Approval",
		"GSD Accommodation Clearance",
		"HR Offboarding Stage",
		"Finance Finalization Stage",
	),
	"Subcontractor Contracts": (),
}


def execute():
	create_workflow_state([{"workflow_state_name": state, "style": style} for state, style in STATES])
	create_workflow_action_master(list(ACTIONS))
	for doctype, rules in RULES.items():
		retire_workflow(doctype, doctype, rules)
		# Close the ToDos the retired assignment rules left open; the process assigns its own tasks.
		if rules:
			frappe.db.set_value(
				"ToDo",
				{"reference_type": doctype, "assignment_rule": ["in", rules], "status": "Open"},
				"status",
				"Closed",
			)
