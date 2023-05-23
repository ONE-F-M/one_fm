import frappe
from frappe import _
from frappe.utils import get_fullname
from one_fm.processor import is_user_id_company_prefred_email_in_employee

def validate_todo(doc, method):
	status_in_db = frappe.db.get_value(doc.doctype, doc.name, 'status')
	if status_in_db != doc.status and doc.assigned_by != doc.allocated_to:
		user = frappe.session.user
		email_content = _("The assignment referenced to {0}({1}) is {2} by {3}".format(doc.reference_type, doc.reference_name, doc.status, get_fullname(user)))
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
