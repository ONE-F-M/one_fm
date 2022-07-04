import frappe
from frappe.utils import getdate, cint, cstr, random_string, now_datetime
import datetime

def response(message, status_code, data=None, error=None):
    """This method generates a response for an API call with appropriate data and status code.

    Args:
        message (str): Message to be shown depending upon API result. Eg: Success/Error/Forbidden/Bad Request.
        status_code (int): Status code of API response.
        data (Any, optional): Any data to be passed as response (Dict, List, etc). Defaults to None.
    """
    frappe.local.response["message"] = message
    frappe.local.response["http_status_code"] = status_code
    frappe.local.response["status_code"] = status_code
    if data:
        frappe.local.response["data"] = data
    elif error:
        frappe.local.response["error"] = error
    return

@frappe.whitelist()
def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
	return user, user_roles, user_employee

def setup_directories():
	"""
		Use this method to create directories needed for the face recognition system: dataset directory and facial embeddings
	"""
	from pathlib import Path
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/user/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/dataset/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/facial_recognition/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/face_rec_temp/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/dataset/"+frappe.session.user+"/").mkdir(parents=True, exist_ok=True)

def validate_date(date: str) -> bool:
    """This method validates a date to be in yyyy-mm-dd format.

    Args:
        date (str): date string

    Returns:
        bool: True/False based on valid date string
    """
    if "-" not in date:
        return False

    date_elements = date.split("-")

    if len(date_elements) != 3:
        return False

    year = date_elements[0]
    month = date_elements[1]
    day = date_elements[2]

    if len(year) != 4:
        return False

    if len(month) > 2:
        return False

    if int(month) > 12 or int(month) < 1:
        return False

    if len(day) > 2:
        return False

    if int(day) > 31 or int(day) < 1:
        return False

    return True


def validate_time(time: str) -> bool:
    """This method validates time to be in format hh:mm:ss

    Args:
        time (str): time string.

    Returns:
        bool: True/False based on valid time string
    """
    if ":" not in time:
        return False

    time_elements = time.split(":")

    if len(time_elements) != 3:
        return False

    hour = time_elements[0]
    minutes = time_elements[1]
    seconds = time_elements[2]

    if len(hour) != 2 or len(minutes) != 2 or len(minutes) != 2 or len(seconds) != 2:
        return False

    if int(hour) > 23 or int(hour) < 0:
        return False

    if int(minutes) > 59 or int(minutes) < 0:
        return False

    if int(seconds) > 59 or int(seconds) < 0:
        return False

    return True

@frappe.whitelist()
def get_current_shift(employee):
	try:
		current_datetime = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
		date, time = current_datetime.split(" ")
		shifts = frappe.get_list("Shift Assignment", {"employee":employee, 'start_date': ['>=', date]}, ["shift", "shift_type"])
		if len(shifts) > 0:
			for shift in shifts:
				time = time.split(":")
				time = datetime.timedelta(hours=cint(time[0]), minutes=cint(time[1]), seconds=cint(time[2]))
				shift_type, start_time, end_time ,before_time, after_time= frappe.get_value("Shift Type", shift.shift_type, ["shift_type","start_time", "end_time","begin_check_in_before_shift_start_time","allow_check_out_after_shift_end_time"])
				#include early entry and late exit time
				start_time = start_time - datetime.timedelta(minutes=before_time)
				end_time = end_time + datetime.timedelta(minutes=after_time)
				if shift_type == "Night":
					if start_time <= time >= end_time or start_time >= time <= end_time:
						return shift
				else:
					if start_time <= time <= end_time:
						return shift
		elif len(shifts)==0:
			return shifts
		else:
			return shifts[0].shift
	except Exception as e:
		print(frappe.get_traceback())
		return frappe.utils.response.report_error(e)


@frappe.whitelist(allow_guest=True)
def get_mobile_version():
    """
        Retrieve the version number of the mobile app
    """
    try:
        version = frappe.db.get_single_value("ONEFM General Setting", 'mobile_app_version')
        return response(message='Successful', status_code=200, data={'version':version}, error=None)
    except Exception as e:
        return response(message='Failed', status_code=500, data={}, error=str(e))


@frappe.whitelist()
def enrollment_status(employee_id: str = None) -> dict:
    """
        Check if an employee is enrolled on the mobile app
    :param employee:
    :return: True or False
    """
    try:
        get_employee = get_employee_by_id(employee_id)
        if get_employee.status:
            employee = frappe.get_doc("Employee", get_employee.message)
            if employee.enrolled and employee.fcm_token:
                return response(message='Employee is enrolled on the mobile app.', status_code=200, data={'enrolled':True}, error=None)
            return response(message='Employee not enrolled.', status_code=get_employee.http_status_code, data={'enrolled':False}, error=None)
        else:
            return response(message=get_employee.message, status_code=get_employee.http_status_code, data={'status':False}, error=None)
    except Exception as e:
        return response(message='Failed', status_code=500, data={}, error=str(e))

@frappe.whitelist()
def enrollment_reset(employee_id: str = None) -> dict:
    """
    Check if an employee is enrolled on the mobile app
    :param employee:
    :return: True or False
    """
    try:
        get_employee = get_employee_by_id(employee_id)
        if get_employee.status:
            employee = frappe.get_doc("Employee", get_employee.message)
            employee.db_set("enrolled", 0)
            return response(message='Enrollment reset successful, re-enrollment can be done by logging off the app then click register',
                status_code=200, data={'status':True}, error=None)
        else:
            return response(message=get_employee.message, status_code=get_employee.http_status_code,
                data={'status':False}, error=None)
    except Exception as e:
        return response(message='Failed', status_code=500, data={}, error=str(e))

@frappe.whitelist()
def get_employee_by_id(employee_id):
    """
    Get employee pk by employee id
    :param employee_id:
    :return:
    """
    try:
        employee = frappe.get_value("Employee", {"employee_id": employee_id}, ["name"], as_dict=1)
        if employee:
            return frappe._dict({'status': True, 'message': employee.name})
        return frappe._dict({'status': False, 'message': f'Employee with ID {employee_id} does not exist', 'http_status_code':404})
    except Exception as e:
        frappe._dict({'status': False, 'message': str(e), 'http_status_code':500})