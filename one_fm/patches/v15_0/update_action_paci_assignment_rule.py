import re

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

# PACI-PRO comes with it. Its close_condition named Draft and Pending GR Operator, and
# close_assignments closes EVERY assignment on the document whichever rule made it - so
# the moment Action PACI assigned the owner in one of those states, PACI-PRO closed it
# again. The states move to unassign_condition, which apply_unassign scopes to the rule's
# own assignment, so the PRO is released without touching anybody else's.
PRO_RULE = "PACI-PRO"
PRO_RULE_FILE = "paci_pro.json"


def execute():
	# The task link is left as it is rather than blanked: it is what the rule would fall back
	# to if it were ever put back on "Based on Process Task", and blanking it is how a rule
	# ends up assigning nobody in the first place.
	for rule_file, name in ((RULE_FILE, RULE), (PRO_RULE_FILE, PRO_RULE)):
		create_assignment_rule(
			get_assignment_rule_json_file(rule_file),
			frappe.db.get_value("Assignment Rule", name, "custom_routine_task"),
		)

	verify()


def verify():
	"""create_assignment_rule logs its failures instead of raising, so check the result."""
	saved = frappe.db.get_value(
		"Assignment Rule", RULE,
		["disabled", "rule", "field", "assign_condition", "unassign_condition"],
		as_dict=True,
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

	# The fixture's day rows used to carry the analyst site's own row names, which Frappe
	# read as existing rows and quietly dropped - leaving the table blank. An empty table
	# still fires every day, so nothing complained until somebody opened the rule.
	days = frappe.db.count("Assignment Rule Day", {"parent": RULE, "parenttype": "Assignment Rule"})
	if days != 7:
		frappe.throw(
			f"WI-002183: {RULE!r} has {days} assignment days rather than 7 - the fixture's "
			"rows were not applied."
		)

	states = {state.state for state in frappe.get_doc("Workflow", "PACI").states}
	for named in re.findall(r'"([^"]+)"', saved.unassign_condition or ""):
		if named not in states:
			frappe.throw(
				f"WI-002183: {RULE!r} unassigns on {named!r}, which the PACI workflow does "
				"not have - it would never release a cancelled record."
			)

	pro = frappe.db.get_value(
		"Assignment Rule", PRO_RULE, ["close_condition", "unassign_condition"], as_dict=True
	)
	if pro:
		for state in ("Draft", "Pending GR Operator"):
			if state in (pro.close_condition or ""):
				frappe.throw(
					f"WI-002183: {PRO_RULE!r} still closes at {state!r}. close_assignments "
					"closes every assignment on the document, so it would take the owner's "
					f"away the moment {RULE!r} made it."
				)
			if state not in (pro.unassign_condition or ""):
				frappe.throw(
					f"WI-002183: {PRO_RULE!r} no longer releases the PRO at {state!r}."
				)

	print(f"WI-002183: {RULE} now assigns the PACI to its owner")
