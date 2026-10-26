import frappe, datetime, requests
from frappe import _
from frappe.utils import getdate, cint, cstr, random_string, now_datetime, strip_html

def response(message, status_code, data=None, error=None, error_code=None):
    """This method generates a response for an API call with appropriate data and status code.

    Args:
        message (str): Message to be shown depending upon API result. Eg: Success/Error/Forbidden/Bad Request.
        status_code (int): Status code of API response.
        data (Any, optional): Any data to be passed as response (Dict, List, etc). Defaults to None.
        error (Any, optional): Human readable reason for the failure, rendered verbatim by the app.
        error_code (str, optional): Stable machine readable reason, so the client can branch on the
            cause instead of pattern matching prose. Eg: INVALID_CREDENTIALS, ACCOUNT_DISABLED.
    """

    #if not status_code in [200, 201]:
    #    frappe.enqueue(frappe.log_error, message=message + "\n" + str(error), title="API Response Error", queue='long')

    try:
        frappe.local.response["message"] = message
        frappe.local.response["http_status_code"] = status_code
        frappe.local.response["status_code"] = status_code
        if error_code:
            frappe.local.response["error_code"] = error_code
        if data:
            frappe.local.response["data"] = data
        elif error:
            # The app renders this slot verbatim. An Exception object is not JSON
            # serialisable, so passing one through - as every `except` branch here does -
            # loses the sentence and the client falls back to "An unexpected error
            # occurred". Coerce so the reason always reaches the employee.
            frappe.local.response["error"] = error if isinstance(error, str) else cstr(error)
        return
    except Exception as e:
        frappe.log_error(title="API Response", message=frappe.get_traceback())


def get_own_employee(employee_id=None):
	"""Return the logged-in user's Employee as name, employee_id and user_id.

	Returns None when the user has no Employee, or when employee_id names a different employee.
	"""
	employee = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, ["name", "employee_id", "user_id"], as_dict=True
	)
	if employee and employee_id and employee_id not in (employee.employee_id, employee.name):
		return None
	return employee


def own_employee_api_enforced():
	"""True when site config enforce_own_employee_api is set; until then mismatches are only logged."""
	return bool(cint(frappe.conf.get("enforce_own_employee_api")))


def log_access_mismatch(reason, target=None):
	"""Log a request the own-employee rules would refuse, once a day per endpoint, caller and target.

	Returns True when the request may go ahead, which is always while enforce_own_employee_api is off.
	"""
	endpoint = frappe.form_dict.get("cmd") or (frappe.request.path if getattr(frappe.local, "request", None) else "")
	key = f"own_employee_check:{endpoint}:{frappe.session.user}:{target}"
	if not frappe.cache.get_value(key):
		frappe.cache.set_value(key, 1, expires_in_sec=86400)
		frappe.log_error(
			title=f"Own employee check: {endpoint}",
			message=frappe.as_json({
				"endpoint": endpoint,
				"user": frappe.session.user,
				"roles": frappe.get_roles(),
				"target": target,
				"reason": reason,
				"enforced": own_employee_api_enforced(),
			}),
		)
	return not own_employee_api_enforced()


def check_own_employee(employee_id=None):
	"""True when employee_id is the caller's, or when it is not and enforcement is off (the mismatch is logged)."""
	if get_own_employee(employee_id):
		return True
	return log_access_mismatch("employee_id is not the logged-in user's employee", employee_id)


def not_own_employee_response():
	"""Answer 403 for a request about an employee who is not the logged-in user."""
	return response(_("Forbidden"), 403, None,
		_("You can only do this for your own account."), error_code="NOT_OWN_EMPLOYEE")


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
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation", "custom_enable_face_recognition", "shift_working"], as_dict=1)
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
        if not employee_id:
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        get_employee = get_employee_by_id(employee_id)
        if get_employee.status:
            employee = frappe.get_doc("Employee", get_employee.message.name)
            if employee.enrolled:
                return response(message=_("Employee is enrolled on the mobile app."), status_code=200, data={'enrolled':True}, error=None)
            return response(message=_("Employee is not enrolled."), status_code=200, data={'enrolled':False}, error=None)
        else:
            return response(_("Employee Not Found"), get_employee.http_status_code,
                            None, get_employee.message)
    except Exception as e:
        frappe.log_error(
            title=f"Mobile API: utils.enrollment_status | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(str(e)) or type(e).__name__)

UPDATE_EMPLOYEE_ROLES = ("Operations Manager", "Projects Manager", "Site Supervisor", "Shift Manager",
	"Shift Supervisor", "HR User", "HR Manager", "System Manager")
UPDATE_EMPLOYEE_FIELDS = ("cell_number", "enrolled")


@frappe.whitelist()
def update_employee(employee_id, field, value):
    """Change another employee's cell_number or reset enrolled, for supervisors and HR (roster and Employee Management pages)."""
    if set(UPDATE_EMPLOYEE_ROLES).isdisjoint(frappe.get_roles()) or field not in UPDATE_EMPLOYEE_FIELDS:
        if not log_access_mismatch(f"update_employee of {field} without a supervisor role or outside {UPDATE_EMPLOYEE_FIELDS}", employee_id):
            frappe.throw(_("You are not allowed to change {0} here.").format(field), frappe.PermissionError)
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
        return frappe._dict({'status': False, 'message': str(e), 'http_status_code':500})



@frappe.whitelist()
def log_error_via_api(traceback: str, message: str, medium: str):
    frappe.log_error(title=f"Error from {medium} -- {frappe.session.user}", message=f"{traceback} -- {message}")
    return response(message="Error Logged Successfully", status_code=201)

@frappe.whitelist()
def google_map_api():
    try:
        api_key = frappe.db.get_single_value("Google Settings", "api_key")
        if not api_key:
            return response(_("Map Unavailable"), 500, None,
                            _("The map service is not configured. Please contact the IT Helpdesk."))
        return response("success", 200, {"google_map_api": api_key})
    except Exception as e:
        frappe.log_error(
            title=f"Mobile API: utils.google_map_api | {frappe.session.user}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(str(e)) or type(e).__name__)


def get_video_extension(video_mime: str = None):
    """Return ".mp4" for a missing value or video/mp4, ".webm" for any video/webm type, else None."""
    if not video_mime:
        return ".mp4"
    mime = cstr(video_mime).strip().lower()
    if mime == "video/mp4":
        return ".mp4"
    if mime.startswith("video/webm"):
        return ".webm"
    return None


def verify_via_face_recogniton_service(url: str, data: dict, files: dict, video_mime: str = None) -> tuple:
    decrypt_video = 1 if type(files.get('video_file'))==str else 0
    data['decrypt_video'] = decrypt_video

    try:
        res = requests.post(url=url, data=data, files=files, timeout=60)
    except requests.exceptions.RequestException:
        frappe.log_error(
            title=f"Mobile API: face recognition service unreachable | {frappe.session.user}",
            message=f"{frappe.get_traceback()}\nvideo_mime: {video_mime}",
        )
        return False, _("Face verification is temporarily unavailable. Please try again in a "
                        "few minutes, or contact your Site Supervisor.")

    if res.status_code == 200:
        api_response = res.json()
        if api_response.get("error"):
            traceback = api_response.get("traceback")
            message = api_response.get("message")
            frappe.log_error(title=f"Error from face recognition system -- {frappe.session.user}", message=f"{traceback} -- {message} -- video_mime: {video_mime}")# if traceback else None
            return False, message
        return True, ""

    return False, _("Face verification is temporarily unavailable. Please try again in a "
                    "few minutes, or contact your Site Supervisor.")

def resolve_active_user(user_id, max_depth=5):
    """
    Resolves the target user. If the user is on leave today, transparently routes
    to their designated Leave Application 'reliever'. Recursively handles chained leaves.
    """
    if not user_id:
        return user_id

    current_user = user_id
    seen_users = {current_user}

    for _ in range(max_depth):
        employee = frappe.db.get_value("Employee", {"user_id": current_user, "status": "Active"}, "name")
        if not employee:
            break

        today = frappe.utils.today()
        active_leave = frappe.get_all(
            "Leave Application",
            filters={
                "docstatus": 1,
                "status": "Approved",
                "employee": employee,
                "from_date": ("<=", today),
                "to_date": (">=", today)
            },
            fields=["custom_reliever_"],
            limit=1
        )

        if not active_leave or not active_leave[0].custom_reliever_:
            break

        reliever_user = frappe.db.get_value("Employee", active_leave[0].custom_reliever_, "user_id")

        if not reliever_user or reliever_user in seen_users:
            break
        
        current_user = reliever_user
        seen_users.add(current_user)

    return current_user
