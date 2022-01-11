import frappe

def response(message, status_code, data=None, error=None):
    """This method generates a response for an API call with appropriate data and status code. 

    Args:
        message (str): Message to be shown depending upon API result. Eg: Success/Error/Forbidden/Bad Request.
        status_code (int): Status code of API response.
        data (Any, optional): Any data to be passed as response (Dict, List, etc). Defaults to None.
    """
    frappe.local.response["message"] = message
    frappe.local.response["http_status_code"] = status_code
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

    