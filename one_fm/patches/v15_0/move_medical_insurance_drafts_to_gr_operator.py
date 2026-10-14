import frappe
import frappe.automation.doctype.assignment_rule.assignment_rule

from one_fm.grd.doctype.preparation.preparation import refresh_row_stage

# A policy opened for a renewal or a local transfer now starts with the GR Operator, who
# applies online themselves. Policies still waiting in the old state are moved over, put on
# the operator's desk and reflected on their Preparation row.
#
# Idempotent: it selects on the old state, so a second run finds nothing to move.

DOCTYPE = "Medical Insurance"
OLD_STATE = "Apply Online by PRO"
NEW_STATE = "Apply Online by GR Operator"


def execute():
	records = frappe.get_all(
		DOCTYPE,
		filters={"workflow_state": OLD_STATE, "docstatus": 0},
		fields=["name", "preparation", "employee"],
	)

	for record in records:
		# update_modified=False: the move is this patch's doing, not an operator's.
		frappe.db.set_value(
			DOCTYPE, record.name, "workflow_state", NEW_STATE, update_modified=False
		)

		document = frappe.get_doc(DOCTYPE, record.name)
		frappe.automation.doctype.assignment_rule.assignment_rule.apply(document)

		refresh_row_stage(record.preparation, record.employee)
