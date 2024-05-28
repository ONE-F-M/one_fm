import frappe, datetime, requests
from frappe.utils import getdate, cint, cstr, random_string, now_datetime

def response(message, status_code, data=None, error=None):
    """This method generates a response for an API call with appropriate data and status code.

    Args:
        message (str): Message to be shown depending upon API result. Eg: Success/Error/Forbidden/Bad Request.
        status_code (int): Status code of API response.
        data (Any, optional): Any data to be passed as response (Dict, List, etc). Defaults to None.
    """

    #if not status_code in [200, 201]:
    #    frappe.enqueue(frappe.log_error, message=message + "\n" + str(error), title="API Response Error", queue='long')

    try:
        frappe.local.response["message"] = message
        frappe.local.response["http_status_code"] = status_code
        frappe.local.response["status_code"] = status_code
        if data:
            frappe.local.response["data"] = data
        elif error:
            frappe.local.response["error"] = error
        return
    except Exception as e:
        frappe.log_error(title="API Response", message=frappe.get_traceback())


def response_dict(message, status_code, data=None, error=None):
    return frappe._dict({
        'status_code': status_code,
        'message': message,
        'data': data,
        'error':error
    })

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
            employee = frappe.get_doc("Employee", get_employee.message.name)
            if employee.enrolled:
                return response(message=f"Employee <b>{employee.employee_name}</b> is enrolled on the mobile app.", status_code=200, data={'enrolled':True}, error=None)
            return response(message=f"Employee <b>{employee.employee_name}</b> is not enrolled.", status_code=200, data={'enrolled':False}, error=None)
        else:
            return response(message=get_employee.message, status_code=get_employee.http_status_code, data={'status':False}, error=None)
    except Exception as e:
        return response(message=str(e), status_code=500, data={'status':False}, error=str(e))

@frappe.whitelist()
def update_employee(employee_id, field, value):
    """
    Check if an employee is enrolled on the mobile app
    :param employee:
    :return: True or False
    """
    try:
        get_employee = get_employee_by_id(employee_id)
        if get_employee.status:
            employee = frappe.get_doc("Employee", get_employee.message.name)
            if (field=='cell_number' and employee.user_id):
                cell_number = int(value)
                cell_number = str(cell_number)
                employee.db_set(field, cell_number)
                user_id = frappe.get_doc("User", employee.user_id)
                user_id.db_set('mobile_no', employee.cell_number)
                user_id.db_set('phone', employee.cell_number)
            else:
                employee.db_set(field, value)
            return response(message=f"Employee <b>{employee.employee_name} -  {field}</b> updated successfully.",
                            status_code=200, data={'status':True}, error=None)
        else:
            return response(message=get_employee.message, status_code=get_employee.http_status_code,
                data={'status':False}, error=None)
    except Exception as e:
        return response(message=str(e), status_code=200, data={'status':False}, error=str(e))

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
            return frappe._dict({'status': True, 'message': employee})
        return frappe._dict({'status': False, 'message': f'Employee with ID {employee_id} does not exist', 'http_status_code':404})
    except Exception as e:
        frappe._dict({'status': False, 'message': str(e), 'http_status_code':500})

@frappe.whitelist()
def google_map_api():
    try:
        return response("success", 200, {
            "google_map_api":frappe.db.get_single_value("Google Settings", "api_key")})
    except Exception as e:
        return response("error", 500, {}, str(e))


@frappe.whitelist()
def log_error_via_api(traceback: str, message: str, medium: str):
    frappe.log_error(title=f"Error from {medium} -- {frappe.session.user}", message=f"{traceback} -- {message}")
    return response(message="Error Logged Successfully", status_code=201)


def verify_via_face_recogniton_service(url: str, data: dict, files: dict) -> tuple:
    res = requests.post(url=url, data=data, files=files)
    if res.status_code == 200:
        api_response = res.json()
        if api_response.get("error"):
            traceback = api_response.get("traceback")
            message = api_response.get("message")
            frappe.log_error(title=f"Error from face recognition system -- {frappe.session.user}", message=f"{traceback} -- {message}") if traceback else None
            return False, message
        return True, ""
    return False, "Facial Recogniton Service is currently available"
