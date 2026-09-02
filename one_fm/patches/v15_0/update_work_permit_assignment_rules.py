import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)

# WI-002182: the Work Permit assignment rules, brought back to the configuration the
# business analyst holds.
#
# Four differences, all of them things a rule was doing that nobody asked it to:
#  - the GR Manager rule also held the permit through "Pending  For Payment", a state the
#    GRD Supervisor moves it out of rather than waits in;
#  - the GR Operator rule took its assignee from a Process Task naming one person, so a
#    permit went to that person whoever raised it. It is back on the owner - the operator
#    who raised the permit is the one who carries it;
#  - the PRO rule is off;
#  - "Work Permit Completion - GR Operator" is not part of the process. It assigned on
#    "Pending Expiry Date Update", a state the Work Permit workflow has no transition into,
#    so it never fired at all.
RULES = (
	"work_permit_gr_manager.json",
	"work_permit_gr_operator.json",
	"work_permit_pro.json",
)

# The rule as it was named before WI-002097's rename reached production by hand. Left
# behind, it would go on assigning the supervisor from the states the new one no longer
# covers.
SUPERSEDED_NAME = "Work Permit - GRD Supervisor"
GR_MANAGER = "Work Permit - GR Manager"

REMOVED_RULE = "Work Permit Completion - GR Operator"

EXPECTED = {
	"Work Permit - GR Manager": {
		"disabled": 0,
		"rule": "Based on Process Task",
		"assign_condition": 'workflow_state in ["Pending GR Manager"]',
	},
	"Work Permit - GR Operator": {"disabled": 0, "rule": "Based on Field", "field": "owner"},
	"Work Permit-PRO": {"disabled": 1, "rule": "Based on Process Task"},
}


def execute():
	carry_the_process_task_across()

	for rule_file in RULES:
		rule = get_assignment_rule_json_file(rule_file)
		# The Process Task link is a site's own - the ids differ between sites - so the
		# fixture does not carry one and the existing link is passed back in. A task-based
		# rule whose task is blanked assigns nobody, and says nothing about it.
		create_assignment_rule(rule, existing_task(rule["name"]))

	if frappe.db.exists("Assignment Rule", SUPERSEDED_NAME):
		frappe.delete_doc("Assignment Rule", SUPERSEDED_NAME, ignore_permissions=True)

	if frappe.db.exists("Assignment Rule", REMOVED_RULE):
		frappe.delete_doc("Assignment Rule", REMOVED_RULE, ignore_permissions=True)

	verify()


def carry_the_process_task_across():
	"""Give the renamed rule the task the old name was pointing at.

	Production renamed this rule by hand and kept its task; a site that did not still has it
	under the old name, and the new one would be created with none.
	"""
	if frappe.db.get_value("Assignment Rule", GR_MANAGER, "custom_routine_task"):
		return

	task = frappe.db.get_value("Assignment Rule", SUPERSEDED_NAME, "custom_routine_task")
	if task and frappe.db.exists("Assignment Rule", GR_MANAGER):
		frappe.db.set_value("Assignment Rule", GR_MANAGER, "custom_routine_task", task)


def existing_task(name):
	return frappe.db.get_value("Assignment Rule", name, "custom_routine_task") or None


def verify():
	"""create_assignment_rule logs its failures instead of raising, so check the result."""
	for name, expected in EXPECTED.items():
		saved = frappe.db.get_value("Assignment Rule", name, list(expected), as_dict=True)
		if not saved:
			frappe.throw(f"WI-002182: assignment rule {name!r} does not exist.")
		for field, value in expected.items():
			if saved.get(field) != value:
				frappe.throw(
					f"WI-002182: {name}.{field} is {saved.get(field)!r}, expected {value!r}."
				)

	for name in (SUPERSEDED_NAME, REMOVED_RULE):
		if frappe.db.exists("Assignment Rule", name):
			frappe.throw(
				f"WI-002182: {name!r} still exists, so two rules would assign the same "
				"Work Permits."
			)

	task = frappe.db.get_value("Assignment Rule", GR_MANAGER, "custom_routine_task")
	if not task:
		frappe.throw(
			f"WI-002182: {GR_MANAGER!r} is Based on Process Task with no task, so it would "
			"assign nobody at Pending GR Manager - silently."
		)
	if not frappe.db.get_value("Process Task", task, "employee_user"):
		frappe.throw(
			f"WI-002182: the Process Task behind {GR_MANAGER!r} names no employee_user, so "
			"the rule would assign nobody."
		)

	print(f"WI-002182: Work Permit assignment rules updated; {GR_MANAGER} -> {task}")
