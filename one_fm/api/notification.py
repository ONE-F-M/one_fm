import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import set_notifications_as_unseen, is_email_notifications_enabled_for_type, send_notification_email
from one_fm.processor import is_user_id_company_prefred_email_in_employee

def create_notification_log(subject, message, for_users, reference_doc, mobile_notification=None, alert=False):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		doc.one_fm_mobile_app = mobile_notification
		# If notification log type is Alert then it will not send email for the log
		if alert:
			doc.type = 'Alert'
		doc.save(ignore_permissions=True)
		frappe.publish_realtime(event='eval_js', message="frappe.show_alert({message: '"+message+"', indicator: 'blue'})", user=user)
	frappe.db.commit()

def get_employee_user_id(employee):
	return frappe.get_value("Employee", {"name": employee}, "user_id")


# This function returns notification list of a given employee.
# params: employee_id (eg: HR-EMP-00003)
# returns: Notification List.
@frappe.whitelist()
def get_notification_list():
	"""
	Returns: notification list
	"""
	try:
		#fetch Site and User ID
		site = frappe.local.conf.app_url
		user_id = frappe.session.user

		#fetch Notification List which were sent to Mobile App
		notification_list = frappe.get_all("Notification Log", filters={'for_user':user_id,'one_fm_mobile_app': 1 }, fields=["name","title","subject","category","creation"])

		# Create Result List
		result = []
		for notification in notification_list:
			notify ={
				"name":notification.name,
				"title" : notification.title,
				"body" : notification.subject,
				"notification_category": notification.category,
				"time": (notification.creation).strftime("%Y-%m-%d %H:%M:%S"),
				"url": site+"app/notification-log/"+notification.name
				}
			result.append(notify)

		if len(notification_list)>0:
			return response("Notifications Are Listed Sucessfully", result, True, 200)
		elif len(notification_list)==0:
			return response("No Notification Yet", notification_list, True, 200)

	except Exception as e:
		frappe.log_error(frappe.get_traceback())
		return response(e, {}, False, 500)

# This function deletes notification of a given `notification_name`
# params: notification_name (eg: b9ddeb43dd)
@frappe.whitelist()
def delete_notification(notification_name):
	"""
	Params:
    notification_name
	"""
	try:
		if frappe.db.exists("Notification Log",{'name':notification_name}):
			frappe.delete_doc("Notification Log", notification_name, ignore_permissions=True)
			frappe.db.commit()

			return response("Notification is Deleted Sucessfully", {}, True, 200)

		elif not frappe.db.exists("Notification Log",{'name':notification_name}):
			return response("Notification Doesn't exist", {}, False, 400)

	except Exception as e:
		frappe.log_error(frappe.get_traceback())
		return response(e, {}, False, 500)

# This method returing the message and status code of the API
def response(message, data, success, status_code):
    """
    Params:
	-------
	message:
	status code: (eg: 200) based on the message
	data: (eg {doctype_list} or {})
	success: (eg: True or False)
    """
    frappe.local.response["message"] = message
    frappe.local.response["data"] = data
    frappe.local.response["success"] = success
    frappe.local.response["http_status_code"] = status_code
    return

def after_insert(doc):
	frappe.publish_realtime("notification", after_commit=True, user=doc.for_user)
	set_notifications_as_unseen(doc.for_user)
	if is_email_notifications_enabled_for_type(doc.for_user, doc.type) and is_user_id_company_prefred_email_in_employee(doc.for_user) :
		try:
			send_notification_email(doc)
		except frappe.OutgoingEmailError:
			doc.log_error(_("Failed to send notification email"))
