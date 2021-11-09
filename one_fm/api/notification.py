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


# This function returns notification list of a given employee.
# params: employee_id (eg: HR-EMP-00003)
# returns: Notification List.
@frappe.whitelist()
def get_notification_list(employee_id):
	"""
	Params:
	employee: employee ERP id 
	Returns: notification list
	"""
	try:
		user_id = frappe.db.get_value("Employee",{'name':employee_id},['user_id'])
		notification_list = frappe.get_all("Notification Log", filters={'for_user':user_id, 'one_fm_mobile_app':1}, fields=["name","subject"])
		if len(notification_list)>0:
			return response("Notifications Are Listed Sucessfully", notification_list, True, 200)
		elif len(notification_list)==0:
			return response("No Notification Yet", notification_list, True, 200)


	except Exception as e:
		frappe.log_error(frappe.get_traceback())
		return response(e, {}, False, 500)

# This method returing the message and status code of the API
def response(message, data, success, status_code):
    """
    Params: message, status code
    """
    frappe.local.response["message"] = message
    frappe.local.response["data"] = data
    frappe.local.response["success"] = success
    frappe.local.response["http_status_code"] = status_code
    return