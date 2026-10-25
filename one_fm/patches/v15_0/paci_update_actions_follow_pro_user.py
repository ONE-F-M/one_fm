"""Show the PACI update actions that match the PRO User field.

In "Pending by GR Operator" the operator saw all four update actions. Update Address and
Update Photo now show only while PRO User is blank, and Update Address By PRO and Update
Photo by PRO only once a PRO User is set.
"""

import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

WORKFLOW = "PACI"
PENDING_GRO = "Pending by GR Operator"

CONDITIONS = {
	"Update Address": 'not doc.get("pro_user")',
	"Update Photo": 'not doc.get("pro_user")',
	"Update Address By PRO": 'doc.get("pro_user")',
	"Update Photo by PRO": 'doc.get("pro_user")',
}


def execute():
	create_workflow(get_workflow_json_file("paci.json"))
	verify()


def verify():
	"""create_workflow logs its failures instead of raising."""
	saved = {
		t.action: t.condition or ""
		for t in frappe.get_doc("Workflow", WORKFLOW).transitions
		if t.state == PENDING_GRO and t.action in CONDITIONS
	}
	for action, condition in CONDITIONS.items():
		if saved.get(action) != condition:
			raise frappe.ValidationError(
				"PACI workflow: {0!r} from {1!r} has condition {2!r}, expected {3!r}.".format(
					action, PENDING_GRO, saved.get(action), condition
				)
			)
