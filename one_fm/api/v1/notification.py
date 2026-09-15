import frappe
from frappe import _
from frappe.utils import cstr, strip_html
from one_fm.api.v1.utils import response

@frappe.whitelist()
def get_notification_list(employee_id: str = None) -> dict:
    """This method returns the list of notifications for a particular user.

    Returns:
        dict: {
			message (str): Brief message indicating the response,
			status_code (int): Status code of response.
			data (List[dict]): List of notification objects -> 
            [
                {
                    name,
                    title,
                    body,
                    notification_category,
                    time,
                    url
                },
            ].
			error (str): Any error handled.
        }
    """
    try:
        if not employee_id:
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if not isinstance(employee_id, str):
            return response(_("Invalid Employee ID"), 400, None,
                            _("Please enter a valid Employee ID."))

        site = frappe.local.conf.app_url

		# notifications created for mobile app
        employee_user_email = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["user_id"])

        if not employee_user_email:
            return response(_("No Login Account"), 404, None,
                            _("No login account is set up for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))
        
        notification_list = frappe.get_all("Notification Log", filters={'for_user': employee_user_email, 'one_fm_mobile_app': 1}, fields=["name", "title", "subject", "category", "creation"])
	
        result = []
        
        if not notification_list or len(notification_list) == 0:
            return response("Success", 200, [{"title": "No notifications found for user {employee_id}".format(employee_id=employee_id)}])
        
        for notification in notification_list:
            notify = {
				"name": notification.name,
				"title": notification.title,
				"body": notification.subject,
				"notification_category": notification.category,
				"time": (notification.creation).strftime("%Y-%m-%d %H:%M:%S"),
				"url": site+"app/notification-log/"+notification.name
			}
            result.append(notify)

        return response("Success", 200, result)

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: notification.get_notification_list | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)