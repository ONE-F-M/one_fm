import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file
from one_fm.utils import create_process_task

# The BA site renamed four states. Everything that stores a state as a string has to
# follow, or the documents sitting in the old ones have no transitions left and stop.
#
# The export also recased "Pending By MOI" to "Pending by MOI". That one is not applied:
# Workflow State is named by its title, MariaDB compares those names case-insensitively,
# and the master is referenced by other doctypes - so the new casing cannot exist
# alongside the old one, and renaming the master reaches outside Visa Request. The state
# keeps the casing the master already has, which is only a label difference; every
# comparison against it is case-sensitive Python, so the fixture, the documents and the
# controller are all held to that one spelling instead.
RENAMED_STATES = {
	"Pending Initial Review": "Pending by GRD Operator",
	"Pending Visa": "Pending Visa Issuance",
	"Pending Visa Request Cancel": "Awaiting Visa Cancellation",
	"Canceled": "Work Permit Cancelled",
}

# Documents are not the only place a state is stored, and every copy has to move:
#  - an open Workflow Action carries the state it was raised from, which is what the
#    action buttons read
#  - Candidate Country Process mirrors the visa's workflow_state into its step status
# Each entry is (doctype, fieldname, extra filters).
HOLDS_A_STATE = (
	("Visa Request", "workflow_state", {}),
	("Workflow Action", "workflow_state", {"reference_doctype": "Visa Request"}),
	("Candidate Country Process Details", "status", {}),
)

OLD_RULE_NAME = "GROperator - Visa Request"
NEW_RULE_NAME = "GRD Operator - Visa Request"

PROCESS_NAME = "Visa"
ERP_DOCUMENT = "Visa Request"

# Rule fixture -> the Process Task it selects its assignee from, and the employee to
# create that task with if the site does not have it yet.
PROCESS_TASK_RULES = [
	{
		"json_file": "grd_operator_visa_request.json",
		"task_description": "Assign Government Relations Operator",
		"employee": "HR-EMP-00775",
	},
	{
		"json_file": "grd_manager_visa_request.json",
		"task_description": "Assign GRD Manager",
		"employee": "HR-EMP-00036",
	},
]

# Selects its assignee from a field, so it needs no task.
FIELD_RULES = ["recruiter_visa_request.json"]


def execute():
	"""Bring the Visa Request workflow, doctype and assignment rules up to the BA site (WI-001773).

	Five workflow states were renamed, so this runs in an order that never leaves a
	document pointing at a state that does not exist: rename the operator rule, apply
	the new workflow definition, move the documents onto the new state names, then
	re-apply the rules whose conditions name them.
	"""
	rename_operator_rule()
	create_workflow(get_workflow_json_file("visa_request.json"))
	migrate_renamed_states()
	normalise_state_casing()
	apply_assignment_rules()


def normalise_state_casing():
	"""Hold every stored state to the exact spelling the workflow uses.

	MariaDB matches these strings case-insensitively, so a document can hold a casing
	the workflow does not have and nothing complains - until code compares it, because
	`doc.workflow_state == "..."` and an assignment rule's `workflow_state in (...)` are
	both case-sensitive. Comparing in Python rather than in a filter is deliberate: a
	filter would match every casing and could not tell which rows are actually wrong.
	"""
	canonical = {
		s.state.lower(): s.state
		for s in frappe.get_doc("Workflow", "Visa Request").states
	}

	for doctype, fieldname, extra in HOLDS_A_STATE:
		if not frappe.db.has_column(doctype, fieldname):
			continue

		rows = frappe.get_all(doctype, filters=extra, fields=["name", fieldname])
		fixed = 0
		for row in rows:
			stored = row.get(fieldname)
			want = canonical.get((stored or "").lower())
			if not want or want == stored:
				continue
			frappe.db.set_value(doctype, row.name, fieldname, want, update_modified=False)
			fixed += 1

		if fixed:
			print(f"WI-001773: recased {doctype}.{fieldname} on {fixed} record(s)")


def rename_operator_rule():
	"""Rename the operator rule rather than replace it.

	ToDo.assignment_rule is a Link, so renaming carries the open assignments across;
	inserting under the new name instead would leave every ToDo raised under the old
	one unable to close.
	"""
	if not frappe.db.exists("Assignment Rule", OLD_RULE_NAME):
		return

	if frappe.db.exists("Assignment Rule", NEW_RULE_NAME):
		# Both present means the rename already happened and something re-created the
		# old one. Leave it disabled rather than delete it, so two rules cannot assign
		# the same states.
		frappe.db.set_value("Assignment Rule", OLD_RULE_NAME, "disabled", 1)
		return

	frappe.rename_doc("Assignment Rule", OLD_RULE_NAME, NEW_RULE_NAME, force=True)


def migrate_renamed_states():
	for doctype, fieldname, extra in HOLDS_A_STATE:
		if not frappe.db.has_column(doctype, fieldname):
			continue

		for old, new in RENAMED_STATES.items():
			filters = {fieldname: old, **extra}
			count = frappe.db.count(doctype, filters)
			if not count:
				continue

			# update_modified stays off: the state name changed, the record did not, and
			# the audit stamp should not read as an edit by whoever ran migrate.
			frappe.db.set_value(doctype, filters, fieldname, new, update_modified=False)
			print(f"WI-001773: {doctype}.{fieldname} {old!r} -> {new!r} on {count} record(s)")


def apply_assignment_rules():
	for rule in PROCESS_TASK_RULES:
		process_task_name = frappe.db.get_value(
			"Process Task",
			{"task": rule["task_description"], "process_name": PROCESS_NAME},
			"name",
		)

		if not process_task_name:
			if not frappe.db.exists("Employee", rule["employee"]):
				# A rule pointing at a task with no assignee silently assigns nobody, so
				# leave the rule alone and say why.
				frappe.log_error(
					title="WI-001773: Visa Process Task not created",
					message=(
						f"Employee {rule['employee']} does not exist, so the Process Task "
						f"\"{rule['task_description']}\" was skipped along with "
						f"{rule['json_file']}."
					),
				)
				continue

			process_task_name = create_process_task(
				process_name=PROCESS_NAME,
				erp_document=ERP_DOCUMENT,
				task_description=rule["task_description"],
				employee=rule["employee"],
				task_type="Repetitive",
				is_routine_task=0,
			).name

		# The task's own assignee is left as the site has it: who covers a tier is the
		# process owner's call, not something this migration should overwrite.
		create_assignment_rule(
			get_assignment_rule_json_file(rule["json_file"]),
			process_task_name=process_task_name,
		)

	for json_file in FIELD_RULES:
		create_assignment_rule(get_assignment_rule_json_file(json_file))
