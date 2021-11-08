import frappe
from frappe import _

def create_notification_log(subject, message, for_users, reference_doc, mobile_notification=None):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		doc.one_fm_mobile_app = mobile_notification
		doc.save(ignore_permissions=True)
		frappe.publish_realtime(event='eval_js', message="frappe.show_alert({message: '"+message+"', indicator: 'blue'})", user=user)
	frappe.db.commit()

def get_employee_user_id(employee):
	return frappe.get_value("Employee", {"name": employee}, "user_id")


# This function returns the list of notification of a given user_id, within the dictionary of "name","subject".
@frappe.whitelist()
def get_notification_list(user_id):
	"""
	Params:
	User id: Employee User ID
	Return: List of Notification
	"""
	try:
		notification_list = frappe.get_all("Notification Log", filters={'for_user':user_id, 'one_fm_mobile_app':1}, fields=["name","subject"])
		if len(notification_list)>0:
			return notification_list 
		else:

			return ('No Notification.')

	except Exception as e:
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(e)