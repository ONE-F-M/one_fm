import frappe 
import pandas as pd
from frappe.workflow.doctype.workflow_action.workflow_action import (
	get_common_email_args, deduplicate_actions, get_next_possible_transitions,
	get_doc_workflow_state, get_workflow_name, get_users_next_action_data
)
import json

def shift_request_submit(self):
	if frappe.db.exists("Shift Assignment", {"employee":self.employee, "start_date":["<=", self.from_date ]}):
		frappe.set_value("Shift Assignment", {"employee":self.employee, "start_date":["<=", self.from_date ]}, "status" , "Inactive")
	
	assignment_doc = frappe.new_doc("Shift Assignment")
	assignment_doc.company = self.company
	assignment_doc.shift = self.operations_shift
	assignment_doc.site = self.operation_site
	assignment_doc.shift_type = self.shift_type
	assignment_doc.employee = self.employee
	assignment_doc.start_date = self.from_date
	assignment_doc.shift_request = self.name
	assignment_doc.insert()
	assignment_doc.submit()
	assignment_doc.end_date = self.to_date
	assignment_doc.submit()
	frappe.db.commit()

@frappe.whitelist()
def fetch_approver(employee):
	if employee:
		shift, department = frappe.get_value("Employee", employee, ["shift","department"])
		if shift:
			shift_supervisor = frappe.get_value("Operations Shift", shift, "supervisor")
			return frappe.get_value("Employee", shift_supervisor, "user_id")
		else:
			approvers = frappe.db.sql(
				"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
				(department),
			)
			approvers = [approver[0] for approver in approvers]
			return approvers[0]

@frappe.whitelist()
def send_workflow_action_email(doc, method):
	recipients = [doc.get("approver")]
	workflow = get_workflow_name(doc.get("doctype"))
	next_possible_transitions = get_next_possible_transitions(
		workflow, get_doc_workflow_state(doc), doc
	)
	user_data_map = get_users_next_action_data(next_possible_transitions, doc)
	
	common_args = get_common_email_args(doc)
	message = common_args.pop("message", None)
	for d in [i for i in list(user_data_map.values()) if i.get('email') in recipients]:
		email_args = {
			"recipients": recipients,
			"args": {"actions": list(deduplicate_actions(d.get("possible_actions"))), "message": message},
			"reference_name": doc.name,
			"reference_doctype": doc.doctype,
		}
		email_args.update(common_args)
		frappe.enqueue(method=frappe.sendmail, queue="short", **email_args)