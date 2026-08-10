import frappe
from frappe.model.rename_doc import get_link_fields, update_link_field_values
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule
)

# "Cleaning Head Supervisor" was never the right name for this role -- the T4
# route it belongs to has always been called "Janitorial" (t4_route ==
# "Janitorial"), and no user was ever actually assigned the role under the
# old name, so this is a pure rename with no assignment data to migrate.
#
# frappe.rename_doc() is not used here: "Workflow State" has allow_rename=0
# (throws outright), and testing showed Role's own rename_doc() call leaves
# an orphaned duplicate without cascading its Link references -- so both
# renames are done directly with the same primitives rename_doc() uses
# internally (get_link_fields/update_link_field_values), which are
# synchronous and don't depend on whatever caused that gap.
RENAMES = [
	("Role", "Cleaning Head Supervisor", "Janitorial Head Supervisor"),
	("Workflow State", "Pending Cleaning Head Supervisor", "Pending Janitorial Head Supervisor"),
]

OLD_ASSIGNMENT_RULES = [
	{"name": "Employee Resignation - Pending Cleaning Head Supervisor"},
	{"name": "Employee Resignation Withdrawal - Pending Cleaning Head Supervisor"},
	{"name": "Employee Resignation Date Adjustment - Pending Cleaning Head Supervisor"},
]
NEW_ASSIGNMENT_RULES = [
	"employee_resignation_pending_janitorial_head_supervisor.json",
	"employee_resignation_withdrawal_pending_janitorial_head_supervisor.json",
	"employee_resignation_date_adjustment_pending_janitorial_head_supervisor.json",
]


def execute():
	for doctype, old, new in RENAMES:
		_rename(doctype, old, new)

	# assign_condition/unassign_condition are plain eval-string fields, not
	# Links -- the rename above can't touch them, so the old rules are
	# replaced outright rather than patched in place.
	for rule in OLD_ASSIGNMENT_RULES:
		delete_assignment_rule(rule)

	for rule_file in NEW_ASSIGNMENT_RULES:
		create_assignment_rule(get_assignment_rule_json_file(rule_file))


def _rename(doctype, old, new):
	if not frappe.db.exists(doctype, old):
		return

	if not frappe.db.exists(doctype, new):
		# Copy the old doc rather than constructing a minimal one -- carries
		# over whatever else is mandatory (e.g. Workflow State.style)
		# without having to enumerate it here.
		new_doc = frappe.copy_doc(frappe.get_doc(doctype, old))
		autoname = frappe.get_meta(doctype).autoname or ""
		if autoname.startswith("field:"):
			new_doc.set(autoname.split(":", 1)[1], new)
		new_doc.insert(set_name=new)

	link_fields = get_link_fields(doctype)
	update_link_field_values(link_fields, old, new, doctype)

	frappe.delete_doc(doctype, old)
