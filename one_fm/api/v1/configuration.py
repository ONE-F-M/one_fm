import frappe, ast, pyotp
from frappe.utils import getdate
from frappe.twofactor import get_otpsecret_for_, process_2fa_for_sms, confirm_otp_token, get_email_subject_for_2fa,get_email_body_for_2fa
from frappe.integrations.oauth2 import get_token
from frappe.core.doctype.user.user import generate_keys
from frappe.utils.background_jobs import enqueue
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.frappeclient import FrappeClient
from frappe.utils import now_datetime
from six import iteritems
from frappe import _
import requests, json
from frappe.utils.password import update_password as _update_password
from twilio.rest import Client as TwilioClient
from one_fm.api.v1.utils import response, get_current_user_details
from one_fm.processor import sendemail, send_whatsapp


def services_hidden_by_role() -> set:
	"""App Services gated on a role the session user does not hold."""
	roles = set(frappe.get_roles())
	return {
		service.name
		for service in frappe.get_all("App Service", filters={"role": ["is", "set"]}, fields=["name", "role"])
		if service.role not in roles
	}


def get_user_app_service():
	user_app_service =  frappe.get_doc("User App Service", {'user':frappe.session.user})
	hidden = services_hidden_by_role()
	return  {
		"name": user_app_service.name,
		"employee": user_app_service.employee,
		"service_detail": [{
			"service":i.service,
			"service_ar": frappe.get_value("Translation", 
                                               {"source_text": i.service, "language": 'ar'}, 
                                               "translated_text") or _(i.service),
			"service_status":i.service_status,
			"service_icon":i.service_icon,
			"auto_assign":i.auto_assign,
			"service_group":i.service_group,
			"service_group_status": i.service_group_status,
			"service_group_icon": i.service_group_icon,
		} for i in user_app_service.service_detail if i.service not in hidden]
    }

@frappe.whitelist()
def app_service_group() -> dict:
	""" This method retrives all app service group.

	Args:

	Returns:
		response (dict): {
			message (str): Brief message indicating the response.
			data (list): [
				{"name":"","icon":"","status":1}
            ]
			error (str)[Optional]: Any error response provided by server. 
		}
	"""
	try:
		app_service_groups = frappe.db.get_all("App Service Group", 
			filters={},
			fields=["name", "icon", "status"])
		for service in app_service_groups:
			service["name_ar"] = frappe.get_value("Translation", 
                                               {"source_text": service["name"], "language": 'ar'}, 
                                               "translated_text") or _(service["name"])
		return response("Success", 200, app_service_groups)
	except Exception as error:
		frappe.log_error(title="Configuration:App Service Group", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def app_version() -> dict:
	"""Return the minimum and latest mobile app versions and store URLs per platform.
	Open to guests because the app checks its version before login."""
	try:
		settings = frappe.get_cached_doc("Mobile App Settings")
		data = {
			"android": {
				"minimum_app_version": settings.android_minimum_version or "",
				"latest_app_version": settings.android_latest_version or "",
				"store_url": settings.play_store_url or "",
			},
			"ios": {
				"minimum_app_version": settings.ios_minimum_version or "",
				"latest_app_version": settings.ios_latest_version or "",
				"store_url": settings.app_store_url or "",
			},
		}
		return response("Success", 200, data)
	except Exception as error:
		frappe.log_error(title="Configuration:App Version", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def app_service() -> dict:
	""" This method retrives all app service.

	Args:

	Returns:
		response (dict): {
			message (str): Brief message indicating the response.
			data (list): [
				{"name":"","icon":"","status":1, "service_group" : "" }
            ]
			error (str)[Optional]: Any error response provided by server. 
		}
	"""
	try:
		employee_id = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["name", "attendance_by_timesheet"], as_dict=1)
		filters = {}
		if employee_id.attendance_by_timesheet:
			filters["assign_to_timesheet_employees"] = 1
		else:
			filters["assign_to_non_timesheet_employees"] = 1

		hidden = services_hidden_by_role()
		app_service = [
			service for service in frappe.db.get_all("App Service",
				filters=filters,
				fields=["name", "icon", "status", "service_group"])
			if service.name not in hidden
		]
		for service in app_service:
			service["name_ar"] = frappe.get_value("Translation", 
                                               {"source_text": service["name"], "language": 'ar'}, 
                                               "translated_text") or _(service["name"])
			service["service_group_ar"] = frappe.get_value("Translation", 
                                               {"source_text": service["service_group"], "language": 'ar'}, 
                                               "translated_text") or _(service["service_group"])
		return response("Success", 200, app_service)
	except Exception as error:
		frappe.log_error(title="Configuration:App Service", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)
	
@frappe.whitelist()
def user_app_service() -> dict:
	""" This method retrives user app service.

	Args:

	Returns:
		response (dict): {
			message (str): Brief message indicating the response.
			data (dict): {}
			error (str)[Optional]: Any error response provided by server. 
		}
	"""
	try:
		employee_id = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["name", "attendance_by_timesheet"], as_dict=1)
		filters = {"auto_assign": 1}
		if employee_id and employee_id.attendance_by_timesheet:
			filters["assign_to_timesheet_employees"] = 1
		else:
			filters["assign_to_non_timesheet_employees"] = 1

		roles = set(frappe.get_roles())
		auto_assign_services = [
			service for service in frappe.db.get_all("App Service", filters=filters, fields=["name", "role"])
			if not service.role or service.role in roles
		]

		if not frappe.db.exists("User App Service", {"user":frappe.session.user}):
			frappe.get_doc({
				"doctype": "User App Service",
				"employee": employee_id.name,
				"user":frappe.session.user,
				"service_detail": [{"service":i.name} for i in auto_assign_services]
            }).insert(ignore_permissions=True)
			frappe.db.commit()
		else:
			# A role-gated service reaches users who gained the role after their list was created.
			user_app_service = frappe.get_doc("User App Service", {"user": frappe.session.user})
			assigned = {row.service for row in user_app_service.service_detail}
			missing = [i.name for i in auto_assign_services if i.role and i.name not in assigned]
			if missing:
				for service in missing:
					user_app_service.append("service_detail", {"service": service})
				user_app_service.save(ignore_permissions=True)
				frappe.db.commit()
		user_app_service = get_user_app_service()
		return response("Success", 200, user_app_service)
	except Exception as error:
		frappe.log_error(title="Configuration:User App Service", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)
	
@frappe.whitelist()
def update_create_user_app_service(service_detail):
	""" This method create, update and retrives user app service.

	Args:
        services (List[Dict]): List of dictionaries containing `service` key with value

	Returns:
		response (dict): {
			message (str): Brief message indicating the response.
			data (dict): {}
			error (str)[Optional]: Any error response provided by server. 
		}
	"""
	try:
		service_detail_type = type(service_detail)
		if (service_detail_type!=list):
			service_detail = json.loads(service_detail)
		for service in service_detail:
			source_text = frappe.get_value(
				"Translation", 
				{"translated_text": service["service"], "language": "ar"}, 
				"source_text"
			)
			if source_text:
				service["service"] = source_text
		if not frappe.db.exists("User App Service", {"user":frappe.session.user}):
			employee_id = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, "name")
			frappe.get_doc({
				"doctype": "User App Service",
				"employee": employee_id,
				"user":frappe.session.user,
				"service_detail": service_detail
            }).insert(ignore_permissions=True)
		else:
			user_app_service = frappe.get_doc("User App Service", frappe.session.user)
			setattr(user_app_service, 'service_detail', [])
			user_app_service.save()
			for i in service_detail:
				user_app_service.append("service_detail", i)
			user_app_service.save()
		frappe.db.commit()
		user_app_service = get_user_app_service()
		return response("Success", 200, user_app_service)
	except Exception as error:
		frappe.log_error(title="Configuration:Create User App Service", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)