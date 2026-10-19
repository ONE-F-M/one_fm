import frappe
from frappe import _
import base64
from datetime import date
import datetime
from one_fm.api.v1.utils import response
from one_fm.api.api import upload_file
from pathlib import Path
import hashlib
import base64, json
from frappe.utils import cint, cstr, getdate, strip_html

@frappe.whitelist()
def get_user_details(employee_id: str = None):
    try:
        if not employee_id:
            return response("Bad Request", 400, None, "Employee ID is required.")

        if not isinstance(employee_id, str):
            return response("Bad Request", 400, None, "Invalid Employee ID format. Please enter a valid value.")

        employee = frappe.get_doc("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee record found for {employee_id}".format(employee_id=employee_id))

        user = frappe.get_doc("User", employee.user_id)

        data = {}
        if user:
                data["name"] = user.full_name
                data["email"] =  user.email
                data["phone_number"] = user.mobile_no
                data["user_image"] = user.user_image
        data["designation"] = employee.designation
        data["employee"] = employee.employee_name

        return response("Success", 200, data)

    except Exception as error:
        frappe.log_error(title="API User", message=frappe.get_traceback())
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def change_user_profile_image(employee_id: str = None, image: str = None):

    if not employee_id:
        return response(_("Missing Employee ID"), 400, None,
                        _("Please enter your Employee ID."))

    if not isinstance(employee_id, str):
        return response(_("Invalid Employee ID"), 400, None,
                        _("Please enter a valid Employee ID."))

    if not image:
        return response(_("No Photo Selected"), 400, None,
                        _("Please choose a photo and try again."))

    if not isinstance(image, str):
        return response(_("Invalid Photo"), 400, None,
                        _("Your photo could not be read. Please choose it again."))

    try:
        try:
            content = base64.b64decode(image)
        except Exception:
            return response(_("Invalid Photo"), 400, None,
                            _("Your photo could not be read. Please retake it and try again."))

        filename = hashlib.md5((employee_id + str(datetime.datetime.now())).encode('utf-8')).hexdigest() + ".png"
        attachment_path = f"/files/profile_image/{employee_id}/{filename}"

        Path(frappe.utils.cstr(frappe.local.site)+f"/public/files/profile_image/{employee_id}").mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE_PATH = frappe.utils.cstr(frappe.local.site)+f"/public/files/profile_image/{employee_id}/{filename}"

        with open(OUTPUT_FILE_PATH, "wb") as fh:
            fh.write(content)

        employee_user = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["user_id"])

        if not employee_user:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        user = frappe.get_doc("User", employee_user)

        if not user:
            return response(_("No Login Account"), 404, None,
                            _("No login account is set up for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        user_image = upload_file(user, "user_image", filename, attachment_path, content, is_private=False)
        user.user_image = user_image.file_url
        user.save()
        frappe.db.commit()

        return response("Success", 201, user.as_dict())

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: user.change_user_profile_image | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)

@frappe.whitelist()
def get_user_roles(employee_id: str = None):
    """This method fetches roles for a given user.

    Args:
        user_id (str): user id (email).

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (List[str]): List of user roles.
            error (str): Any error handled.
        }
    """
    try:
        employee_user = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["user_id"])

        if not employee_user:
            return response("Resource Not Found", 404, None, "No employee record found with {employee_id}".format(employee_id=employee_id))
        
        user_roles = frappe.get_roles(employee_user)
        
        return response("Success", 200, user_roles)
    except Exception as e:
        frappe.log_error(title="API User roles", message=frappe.get_traceback())

@frappe.whitelist()
def store_fcm_token(employee_id: str = None , fcm_token: str = None, device_os: str = None):
    try:
        if not employee_id:
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if not fcm_token:
            return response(_("Missing Device Token"), 400, None,
                            _("Your device could not be registered for notifications. Please try again."))

        if not device_os:
            return response(_("Missing Device Type"), 400, None,
                            _("Your device could not be registered for notifications. Please try again."))

        if not isinstance(employee_id, str):
            return response(_("Invalid Employee ID"), 400, None,
                            _("Please enter a valid Employee ID."))

        employee_name = frappe.db.get_value("Employee", {"employee_id": employee_id}, "name") \
            or frappe.db.get_value("Employee", {"name": employee_id}, "name")
        if not employee_name:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. "
                              "Please contact the IT Helpdesk.").format(employee_id))

        employee = frappe.get_doc("Employee", employee_name)
        
        
        employee.db_set('device_os',device_os)
        employee.db_set('fcm_token',fcm_token)
       
        frappe.db.commit()
        return response("Success", 201, employee.as_dict())

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: user.store_fcm_token | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)
    