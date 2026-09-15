import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	delete_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002186: an On the Job Training request is approved by the manager of the project the
# trainee's shift belongs to, not by the Operations Manager.
#
# The manager reaches the record by fetch - Operations Role names the shift, the shift names
# the project, the project names its manager, and the manager names their user - and the
# assignment rule assigns that user. The BA export left the Employee link without a
# fetch_from, which would have left the whole chain empty and the rule assigning nobody, so
# it mirrors Client Event's chain instead (agreed with the process owner).
WORKFLOW_FILE = "on_the_job_training.json"

NEW_RULE_FILE = "assigning_project_manager_for_approval.json"
NEW_RULE = "Assigning Project Manager for Approval"
OLD_RULE = "Assigning Operations Manager for Approval"
SUPERVISOR_RULE_FILE = "returning_to_operations_supervisor_of_ojt_request.json"

EXPECTED_FIELDS = {
	"project_manager_employee": "project.project_manager",
	"project_manager": "project_manager_employee.user_id",
}


def execute():
	frappe.reload_doc("one_fm", "doctype", "on_the_job_training")

	create_workflow(get_workflow_json_file(WORKFLOW_FILE))

	for rule_file in (NEW_RULE_FILE, SUPERVISOR_RULE_FILE):
		rule = get_assignment_rule_json_file(rule_file)
		create_assignment_rule(
			rule, frappe.db.get_value("Assignment Rule", rule["name"], "custom_routine_task")
		)

	# Left behind, the old rule would go on assigning the Operations Manager at the same
	# state the new one assigns the Project Manager - two rules, one queue, split in half.
	if frappe.db.exists("Assignment Rule", OLD_RULE):
		delete_assignment_rule({"name": OLD_RULE})

	verify()


def verify():
	"""create_workflow and create_assignment_rule log their failures instead of raising."""
	meta = frappe.get_meta("On the Job Training")
	for fieldname, fetch_from in EXPECTED_FIELDS.items():
		field = meta.get_field(fieldname)
		if not field:
			frappe.throw(f"WI-002186: On the Job Training has no {fieldname!r} field.")
		if field.fetch_from != fetch_from:
			frappe.throw(
				f"WI-002186: {fieldname}.fetch_from is {field.fetch_from!r}, expected "
				f"{fetch_from!r} - the manager would never reach the record."
			)

	workflow = frappe.get_doc("Workflow", "On the Job Training")
	approvers = {
		t.allowed for t in workflow.transitions
		if t.state in ("Pending Approval", "Pending Extension Approval")
	}
	if "Operations Manager" in approvers:
		frappe.throw(
			"WI-002186: the Operations Manager still approves an OJT request."
		)
	if "Project Manager" not in approvers:
		frappe.throw("WI-002186: no Project Manager transition out of Pending Approval.")

	rule = frappe.db.get_value(
		"Assignment Rule", NEW_RULE, ["disabled", "rule", "field"], as_dict=True
	)
	if not rule:
		frappe.throw(f"WI-002186: assignment rule {NEW_RULE!r} was not created.")
	if rule.disabled:
		frappe.throw(f"WI-002186: {NEW_RULE!r} is disabled.")
	if rule.rule != "Based on Field" or rule.field != "project_manager":
		frappe.throw(
			f"WI-002186: {NEW_RULE!r} reads {rule.field!r} rather than the project manager, "
			"so it would assign nobody."
		)
	if frappe.db.exists("Assignment Rule", OLD_RULE):
		frappe.throw(
			f"WI-002186: {OLD_RULE!r} still exists, so two rules would assign the same "
			"requests at Pending Approval."
		)

	print("WI-002186: On the Job Training approvals route to the Project Manager")
