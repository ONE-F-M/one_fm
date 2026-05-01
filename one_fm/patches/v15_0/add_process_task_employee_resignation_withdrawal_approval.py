import frappe
from one_fm.utils import create_process_task as _create_process_task

def execute():
	process_task = get_or_create_process_task()
	
	assignment_rule_name = "Employee Resignation Withdrawal - Pending Operations Manager"
	if frappe.db.exists("Assignment Rule", assignment_rule_name):
		return

	assignment_rule_data = {
		"doctype": "Assignment Rule",
		"name": assignment_rule_name,
		"document_type": "Employee Resignation Withdrawal",
		"priority": 0,
		"disabled": 0,
		"description": """<p>Here is to inform you that the following {{ doctype }}({{ name }}) requires your attention/action.
        <br>
        The details of the request are as follows:
        <br>
        </p><table cellpadding="0" cellspacing="0" border="1" style="border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Label</th>
                    <th style="padding: 10px; text-align: left; background-color: #f2f2f2;">Value</th>
                </tr>
            </thead>
        <tbody>
        
            <tr>
                <td style="padding: 10px;">Employee Resignation</td>
                <td style="padding: 10px;">{{employee_resignation}}</td>
            </tr>
            
            <tr>
                <td style="padding: 10px;">Employee</td>
                <td style="padding: 10px;">{{employee}}</td>
            </tr>
            
            <tr>
                <td style="padding: 10px;">Full Name in English</td>
                <td style="padding: 10px;">{{full_name_in_english}}</td>
            </tr>
            
            <tr>
                <td style="padding: 10px;">Relieving Date</td>
                <td style="padding: 10px;">{{relieving_date}}</td>
            </tr>
            
            <tr>
                <td style="padding: 10px;">Reason</td>
                <td style="padding: 10px;">{{reason}}</td>
            </tr>
            </tbody></table><p></p>""",
		"is_assignment_rule_with_workflow": 0,
		"assign_condition": "workflow_state == \"Pending Operations Manager\"",
		"unassign_condition": "workflow_state != \"Pending Operations Manager\"",
		"rule": "Based on Process Task",
		"custom_routine_task": process_task.name,
		"field": "supervisor",
		"last_user": "abdullah@one-fm.com",
		"assignment_days": [
			{"day": "Monday"},
			{"day": "Tuesday"},
			{"day": "Wednesday"},
			{"day": "Thursday"},
			{"day": "Friday"},
			{"day": "Saturday"},
			{"day": "Sunday"}
		]
	}
	frappe.get_doc(assignment_rule_data).insert(ignore_permissions=True)

def get_or_create_process_task():
	process_name = "Resignation"
	erp_document = "Employee Resignation Withdrawal"
	task_description = "Review Resignation Withdrawal Action - Operations Manager"

	existing_task = frappe.db.get_value("Process Task", {
		"process_name": process_name,
		"erp_document": erp_document,
		"task": task_description
	}, "name")

	if existing_task:
		return frappe.get_doc("Process Task", existing_task)

	return _create_process_task(
		process_name=process_name,
		erp_document=erp_document,
		task_description=task_description,
		employee="HR-EMP-00001"
	)

