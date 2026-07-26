import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

WORKFLOW_NAME = "Employee Schedule Suspension"

# WI-001694 names four approver roles for the Approve/Reject transitions. Every role a
# Workflow Transition references must exist, or the whole Workflow insert fails link
# validation - and create_workflow() swallows that into an Error Log, so migrate reports
# success while nothing is installed. "Operations Admin" does not exist on every site, so
# it is created here (empty, for an administrator to assign users to).
APPROVER_ROLES = [
	"Operations Manager",
	"Operations Admin",
	"General Manager",
	"System Manager",
]


def create_missing_approver_roles():
	for role in APPROVER_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def execute():
	"""WI-001694: install the Employee Schedule suspension approval workflow.

	States: Active -> Pending Suspension -> (Approve) Suspended / (Reject) Active.
	Employee Availability is only changed to "Suspended" on approval.
	"""
	create_missing_approver_roles()

	create_workflow(get_workflow_json_file("employee_schedule.json"))
	frappe.clear_cache(doctype="Employee Schedule")

	# create_workflow() logs and swallows any failure, which previously left the roster
	# raising "Unknown column 'workflow_state'" after a clean-looking migrate. Fail the
	# patch instead, so a broken install cannot pass unnoticed.
	if not frappe.db.exists("Workflow", WORKFLOW_NAME):
		frappe.throw(
			f"{WORKFLOW_NAME} workflow was not installed. "
			"See the 'Workflow Creation Error' entry in Error Log for the cause."
		)
