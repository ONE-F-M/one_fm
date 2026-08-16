from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

# Employee Resignation's own T4 path already says "Approve" -- Withdrawal's
# Pending Supervisor / Pending T4 Admin transitions were still labelled
# "Forward" from before that rename, so the two doctypes read inconsistently.


def execute():
	create_workflow(get_workflow_json_file("employee_resignation_withdrawal.json"))
