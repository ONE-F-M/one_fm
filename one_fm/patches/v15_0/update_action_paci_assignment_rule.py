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

	verify_holds_and_releases(RULE, saved.assign_condition, saved.unassign_condition)

	verify_pro_rule()
	verify_holds_and_releases(PRO_RULE, *frappe.db.get_value(
		"Assignment Rule", PRO_RULE, ["assign_condition", "unassign_condition"]))

	print(f"WI-002183: {RULE} now assigns the PACI to its owner")


def verify_holds_and_releases(name, assign_condition, unassign_condition):
	"""A rule holds a document while it is that person's, and lets go when it is not.

	Every state has to fall on one side or the other. A state where it neither assigns nor
	releases leaves whoever it assigned still holding a document that has moved past them -
	and, worse, apply() never reaches its assign pass while an assignment is standing, so
	the rule that should take over next cannot.

	Checked against the states the workflow actually has, rather than by matching text: a
	condition written as the mirror of its own assign names no state at all.
	"""
	for state in {state.state for state in frappe.get_doc("Workflow", "PACI").states}:
		context = {"workflow_state": state}
		holds = bool(frappe.safe_eval(assign_condition, None, context))
		releases = bool(unassign_condition and frappe.safe_eval(unassign_condition, None, context))

		if holds and releases:
			frappe.throw(f"WI-002183: {name!r} both assigns and releases at {state!r}.")
		if not holds and not releases:
			frappe.throw(
				f"WI-002183: {name!r} neither assigns nor releases at {state!r}, so it would "
				"go on holding a PACI that has moved past it - and block the rule that "
				"should take over."
			)


def verify_pro_rule():
	"""The PRO holds a PACI while it is theirs, and lets go the moment it is not.

	Checked by evaluating the conditions against every state the workflow has rather than
	by matching their text: the rule is the mirror of its own assign condition now, so
	looking for a state name in it would find nothing and prove nothing.
	"""
	pro = frappe.db.get_value(
		"Assignment Rule", PRO_RULE,
		["assign_condition", "unassign_condition", "close_condition"], as_dict=True,
	)
	if not pro:
		return

	for state in {state.state for state in frappe.get_doc("Workflow", "PACI").states}:
		context = {"workflow_state": state}

		# close_assignments closes every assignment on the document, whichever rule made
		# it, so this rule may not close anywhere at all - Action PACI owns the terminal
		# state.
		if pro.close_condition and frappe.safe_eval(pro.close_condition, None, context):
			frappe.throw(
				f"WI-002183: {PRO_RULE!r} closes at {state!r}. close_assignments closes "
				f"every assignment on the document, so it would take {RULE!r}'s away."
			)


