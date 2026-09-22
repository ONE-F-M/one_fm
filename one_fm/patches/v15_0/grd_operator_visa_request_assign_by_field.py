"""WI-002610: assign the Visa Request from grd_operator rather than from the Process Task.

Migrating the configuration the Process Owner approved on the BA site. Everything else on
the rule - both conditions, the description, all seven assignment days, the empty users
table - is already byte-identical to the BA's version; the only difference is how the
assignee is chosen.

Converted in place rather than added alongside. The BA site carries the change as a second
rule named "GRD Operator - Visa Requests" with the old one disabled, but the names would
then differ by a single trailing "s", and two rules that read almost the same are how the
wrong one gets edited later - or, if both are ever enabled, how one request gets assigned
twice. Confirmed with the requester before writing this.

"GRD Manager - Visa Request" is deliberately untouched. It is disabled on the BA site and
enabled here, but this story is about the Operator rule, and turning the Manager rule off
would stop assignments on Pending GRD Manager Approval - which is precisely the kind of
"negatively affected" the criteria rule out.

custom_routine_task is left pointing at the Process Task it always did. With rule set to
Based on Field it is not read, and clearing it would be a change nobody asked for.
"""

import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)

RULE = "GRD Operator - Visa Request"
FIELD = "grd_operator"
RULE_TYPE = "Based on Field"


def execute():
	if not frappe.db.exists("Assignment Rule", RULE):
		# Nothing to convert. The rule is created by
		# add_assignment_rule_groperator_visa_request, which runs earlier.
		return

	create_assignment_rule(get_assignment_rule_json_file("grd_operator_visa_request.json"))

	# create_assignment_rule swallows its exceptions into an Error Log, so a failure here
	# is otherwise invisible - the migration "passes" and the rule keeps assigning to the
	# Process Task's owner. Read it back and say so plainly instead.
	applied = frappe.db.get_value("Assignment Rule", RULE, ["rule", "field"], as_dict=True)
	if not applied or applied.rule != RULE_TYPE or applied.field != FIELD:
		frappe.throw(
			f"{RULE} was not converted: expected {RULE_TYPE}/{FIELD}, "
			f"found {applied and applied.rule}/{applied and applied.field}. "
			"See the Error Log for the underlying failure."
		)
