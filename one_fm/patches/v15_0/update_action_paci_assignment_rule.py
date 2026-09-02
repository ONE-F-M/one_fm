import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)

# WI-002183: "Action PACI" takes its assignee from the record's owner rather than from a
# Process Task, which is what the business analyst's copy of the rule holds.
#
# It is also the only thing that makes the rule work at all right now. The rule is "Based on
# Process Task" with **no task linked**, and AssignmentRule.apply reads the assignee off the
# task - so every PACI raised since has been assigned to nobody, with no error and nothing in
# the log to say so. The states it fires on are unchanged; only where the name comes from is.
RULE = "Action PACI"
RULE_FILE = "action_paci.json"


def execute():
	# The task link is left as it is rather than blanked: it is what the rule would fall back
	# to if it were ever put back on "Based on Process Task", and blanking it is how a rule
	# ends up assigning nobody in the first place.
	create_assignment_rule(
		get_assignment_rule_json_file(RULE_FILE),
		frappe.db.get_value("Assignment Rule", RULE, "custom_routine_task"),
	)

	verify()


def verify():
	"""create_assignment_rule logs its failures instead of raising, so check the result."""
	saved = frappe.db.get_value(
		"Assignment Rule", RULE, ["disabled", "rule", "field", "assign_condition"], as_dict=True
	)
	if not saved:
		frappe.throw(f"WI-002183: assignment rule {RULE!r} does not exist.")
	if saved.disabled:
		frappe.throw(f"WI-002183: assignment rule {RULE!r} is disabled.")
	if saved.rule != "Based on Field":
		frappe.throw(f"WI-002183: {RULE!r} is still {saved.rule!r}.")
	if saved.field != "owner":
		frappe.throw(
			f"WI-002183: {RULE!r} is Based on Field with field {saved.field!r}, so it would "
			"assign nobody."
		)
	if "Pending GR Operator" not in (saved.assign_condition or ""):
		frappe.throw(f"WI-002183: {RULE!r} no longer fires at Pending GR Operator.")

	print(f"WI-002183: {RULE} now assigns the PACI to its owner")
