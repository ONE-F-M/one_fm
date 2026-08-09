from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

# Employee Resignation Withdrawal and Employee Resignation Date Adjustment had
# no "Draft" state -- both landed straight into their first review state the
# moment the document was created, with no chance to save an incomplete
# request and come back to it later, unlike Employee Resignation itself.
# This adds a Draft state + "Submit for Review" action to both, matching
# Employee Resignation's own pattern.


def execute():
	create_workflow(get_workflow_json_file("employee_resignation_withdrawal.json"))
	create_workflow(get_workflow_json_file("employee_resignation_date_adjustment.json"))
