import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002136: PACI charges nothing for some transactions, and the workflow had no way out of
# Pending GR Operator that did not owe a payment invoice. It also routed a saved application
# on the role of whoever pressed Save rather than on its Category. The doctype reload picks
# up the No Payment Required and PRO User fields the rules read.
WORKFLOW = "PACI"
NO_PAYMENT_TRANSITION = ("Pending GR Operator", "No Payment Required", "Completed")
CONDITIONED_TRANSITIONS = {
	("Draft", "Save", "Pending GR Operator"): 'doc.category in ("Renewal", "Transfer")',
	("Draft", "Save", "Pending PRO"): 'doc.category == "New Application"',
	NO_PAYMENT_TRANSITION: "doc.no_payment_required",
}


def execute():
	frappe.reload_doc("grd", "doctype", "paci")

	create_workflow(get_workflow_json_file("paci.json"))
	verify()


def verify():
	"""Checked after the fact - create_workflow logs its failures instead of raising, so it
	can report success having changed nothing."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)
	transitions = {(t.state, t.action, t.next_state): (t.condition or "") for t in workflow.transitions}

	if NO_PAYMENT_TRANSITION not in transitions:
		frappe.throw(
			f"WI-002136: {NO_PAYMENT_TRANSITION} is missing from the {WORKFLOW} workflow - "
			"check the Error Log. Without it a fee-free civil ID cannot be completed."
		)

	wrong = [
		key for key, condition in CONDITIONED_TRANSITIONS.items()
		if transitions.get(key) != condition
	]
	if wrong:
		frappe.throw(
			f"WI-002136: {wrong} carry a missing or wrong condition. A Save transition "
			"without one routes every application to whichever desk it matches first, and "
			'"No Payment Required" without one offers the button to records that owe a fee.'
		)
