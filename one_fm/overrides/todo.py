import frappe
from frappe import _
from frappe.utils import get_fullname
from one_fm.processor import is_user_id_company_prefred_email_in_employee

def validate_todo(doc, method):
	notify_todo_status_change(doc)
	set_todo_type_from_refernce_doc(doc)

def notify_todo_status_change(doc):
	if doc.is_new():
		return
	status_in_db = frappe.db.get_value(doc.doctype, doc.name, 'status')
	if status_in_db != doc.status and doc.assigned_by != doc.allocated_to:
		user = frappe.session.user
		email_content = _("""
                    	The assignment referenced to {0}({1}) is {2} by {3}. See Details Below <br> 
					<p>Description: {4} </p> <br>
					<p>Date of Allocation:{5}</p> <br>
					<p>Due Date:{6}</p> <br>
                     """.format(doc.reference_type, doc.reference_name, doc.status,\
                         	get_fullname(user),doc.description,doc.creation,doc.date))
		if doc.reference_type == "Task":
			email_content+= f'<p>Subject:{frappe.db.get_value("Task",{doc.reference_name},"subject")}</p>'
		notification_log = frappe.new_doc('Notification Log')
		notification_log.subject = _("{0}({1}) assignment is {2}".format(doc.reference_type, doc.reference_name, doc.status))
		notification_log.email_content = email_content
		notification_log.for_user = doc.assigned_by
		notification_log.document_type = doc.doctype
		notification_log.document_name = doc.name
		notification_log.from_user = user
		# If notification log type is Alert then it will not send email for the log
		if send_notification_alert_only(doc.assigned_by):
			notification_log.type = 'Alert'
		else:
			notification_log.type = 'Assignment'
		notification_log.insert(ignore_permissions=True)

def send_notification_alert_only(user):
	if user == 'Administrator':
		return True
	if not is_user_id_company_prefred_email_in_employee(user):
		return True
	return False

def set_todo_type_from_refernce_doc(doc):
	if doc.reference_type and doc.reference_name:
		if doc.reference_type in ['Project', 'Task'] and frappe.get_meta(doc.reference_type).has_field('type'):
			doc.type = frappe.db.get_value(doc.reference_type, doc.reference_name, 'type')
		else:
			doc.type = "Action"
