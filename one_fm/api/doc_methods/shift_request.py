import frappe, json
from frappe import _
import pandas as pd
from frappe.workflow.doctype.workflow_action.workflow_action import (
	get_common_email_args, deduplicate_actions, get_next_possible_transitions,
	get_doc_workflow_state, get_workflow_name, get_users_next_action_data
)
from frappe.utils import getdate, today, cstr
from frappe.model.workflow import apply_workflow
from one_fm.utils import (workflow_approve_reject, send_workflow_action_email)
from one_fm.api.notification import create_notification_log, get_employee_user_id


def shift_request_submit(self):
	if self.workflow_state != 'Update Request':
		self.db_set("status", self.workflow_state)
	
	if self.from_date == cstr(getdate()):
		if frappe.db.exists("Shift Assignment", {"employee":self.employee, "start_date": self.from_date, "docstatus": 1}):
			frappe.set_value("Shift Assignment", {"employee":self.employee, "start_date": self.from_date }, "status" , "Inactive")
		if self.workflow_state == 'Approved':
			create_shift_assignment_from_request(self)

def validate_default_shift(self):
	default_shift = frappe.get_value("Employee", self.employee, "default_shift")
	if self.shift_type == default_shift:
		pass

def on_update(doc, event):
	if doc.workflow_state in ['Approved', 'Rejected']:
		workflow_approve_reject(doc, [get_employee_user_id(doc.employee)])

	if doc.workflow_state == 'Draft':
		send_workflow_action_email(doc,[doc.approver])

def shift_request_cancel(self):
	'''
		Method used to override Shift Request on_cancel
	'''
	cancel_shift_assignment_of_request(self)

def on_update_after_submit(doc, method):
	if doc.update_request:
		if doc.workflow_state == 'Approved':
			doc.db_set("status", 'Approved')
			create_shift_assignment_from_request(doc)
		if doc.workflow_state == 'Update Request':
			doc.db_set("status", 'Draft')
			cancel_shift_assignment_of_request(doc)

def create_shift_assignment_from_request(shift_request, submit=True):
	'''
		Method used to create Shift Assignment from Shift Request
		args:
			shift_request: Object of shift request
			submit: Boolean
	'''
	assignment_doc = frappe.new_doc("Shift Assignment")
	assignment_doc.company = shift_request.company
	assignment_doc.shift = shift_request.operations_shift
	assignment_doc.shift_type = shift_request.shift_type
	assignment_doc.employee = shift_request.employee
	assignment_doc.start_date = shift_request.from_date
	assignment_doc.shift_request = shift_request.name
	assignment_doc.check_in_site = shift_request.check_in_site
	assignment_doc.check_out_site = shift_request.check_out_site
	assignment_doc.insert()
	if submit:
		assignment_doc.submit()
	frappe.db.commit()

def cancel_shift_assignment_of_request(shift_request):
	'''
		Method used to cancel Shift Assignment of a Shift Request
		args:
			shift_request: Object of shift request
			submit: Boolean
	'''
	schedule_exists = frappe.db.exists("Employee Schedule",{"employee":shift_request.employee, "date":cstr(getdate()), "employee_availability":"Working"})

	shift_assignment_list = frappe.get_list(
		"Shift Assignment",
		{
			"employee": shift_request.employee,
			"shift_request": shift_request.name,
			"docstatus": 1
		}
	)
	if shift_assignment_list:
		for shift in shift_assignment_list:
			shift_assignment_doc = frappe.get_doc("Shift Assignment", shift["name"])
			shift_assignment_doc.cancel()
	if shift_request.from_date <= cstr(getdate()) <= shift_request.to_date and schedule_exists:
		schedule = frappe.get_doc("Employee Schedule",{"employee":shift_request.employee, "date":cstr(getdate())})
		if schedule:
			sa = frappe.get_doc(dict(
            doctype='Shift Assignment',
			start_date = cstr(getdate()),
			employee = schedule.employee,
			employee_name = schedule.employee_name,
			department = schedule.department,
			operations_role = schedule.operations_role,
			shift = schedule.shift,
			site = schedule.site,
			project = schedule.project,
			shift_type = schedule.shift_type,
			roster_type = schedule.roster_type,
        	)).insert()
			sa.submit()


def validate_approver(self):
	shift, department = frappe.get_value("Employee", self.employee, ["shift","department"])

	approvers = frappe.db.sql(
		"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
		(department),
	)

	approvers = [approver[0] for approver in approvers]

	if frappe.db.exists("Employee", self.employee,["reports_to"]):
		report_to = frappe.get_value("Employee", self.employee,["reports_to"])
		approvers.append(frappe.get_value("Employee", report_to, "user_id"))


	if shift:
			shift_supervisor = frappe.get_value("Operations Shift", shift, "supervisor")
			approvers.append(frappe.get_value("Employee", shift_supervisor, "user_id"))

	if self.approver not in approvers:
		frappe.throw(_("Only Approvers can Approve this Request."))

@frappe.whitelist()
def fetch_approver(employee):
	if employee:
		reports_to = frappe.get_value("Employee", employee,["reports_to"])
		if reports_to:
			return frappe.get_value("Employee", reports_to, "user_id")

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

def fill_to_date(doc, method):
	if not doc.to_date:
		doc.to_date = doc.from_date


@frappe.whitelist()
def update_request(shift_request, from_date, to_date):
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if getdate(today()) > from_date:
		frappe.throw('From Date cannot be before today.')
	if from_date > to_date:
		frappe.throw('To Date cannot be before From Date.')
	shift_request_obj = frappe.get_doc('Shift Request', shift_request)
	shift_request_obj.db_set("from_date", from_date)
	shift_request_obj.db_set("to_date", to_date)
	shift_request_obj.db_set("update_request", True)
	shift_request_obj.db_set("status", 'Draft')
	apply_workflow(shift_request_obj, "Update Request")
