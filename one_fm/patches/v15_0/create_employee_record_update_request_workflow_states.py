import frappe

# The Employee Record Update Request workflow (a Processa map imported by hand)
# links to these Workflow State masters. A state that has no master cannot be used, and
# Workflow State.style is mandatory on this site, so every state is created with a style.
#
# A state that already exists is left exactly as it is: Draft, Completed, Rejected by ...
# are shared with other workflows and must not be restyled from here.
WORKFLOW_STATES = {
	"Draft": "Danger",
	"Pending Line Manager": "Danger",
	"Pending Finance Manager": "Warning",
	"Pending General Manager": "Warning",
	"Pending Record Update": "Primary",
	"Pending HR Action": "Inverse",
	"Completed": "Success",
	"Rejected by Line Manager": "Danger",
	"Rejected by Finance Manager": "Danger",
	"Rejected by General Manager": "Danger",
}


def execute():
	for state, style in WORKFLOW_STATES.items():
		if frappe.db.exists("Workflow State", state):
			continue
		frappe.get_doc({
			"doctype": "Workflow State",
			"workflow_state_name": state,
			"style": style,
		}).insert(ignore_permissions=True)
