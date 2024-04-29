import frappe
import base64
from datetime import date
import datetime
from one_fm.api.v1.utils import response
from one_fm.api.api import upload_file
from pathlib import Path
import hashlib
import base64, json
from frappe.utils import cint, cstr, getdate

@frappe.whitelist()
def get_user_details(employee_id: str = None):
    try:
        if not employee_id:
            return response("Bad Request", 400, None, "employee_id required.")

        if not isinstance(employee_id, str):
            return response("Bad Request", 400, None, "employee_id must be of type str.")

        if not frappe.db.exists("Employee", employee_id):
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        employee = frappe.get_doc("Employee", employee_id)



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
        return response("Bad Request", 400, None, "user_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "user_id must be of type str.")

    if not image:
        return response("Bad Request", 400, None, "image required.")

    if not isinstance(image, str):
        return response("Bad Request", 400, None, "image must be of type str.")
    
    content = base64.b64decode(image)
    filename = hashlib.md5((employee_id + str(datetime.datetime.now())).encode('utf-8')).hexdigest() + ".png"
    attachment_path = f"/files/profile_image/{employee_id}/{filename}"

    Path(frappe.utils.cstr(frappe.local.site)+f"/public/files/profile_image/{employee_id}").mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE_PATH = frappe.utils.cstr(frappe.local.site)+f"/public/files/profile_image/{employee_id}/{filename}"
    
    with open(OUTPUT_FILE_PATH, "wb") as fh:
        fh.write(content)

    try:
        employee_user = frappe.db.get_value("Employee", {"name": employee_id}, ["user_id"])

        if not employee_user:
            return response("Resource Not Found", 404, None, "No user found with {employee_id}".format(employee_id=employee_id))

        user = frappe.get_doc("User", employee_user)

        if not user:
            return response("Resource Not Found", 404, None, "No user found with {user_id}".format(user_id = employee_id))

        user_image = upload_file(user, "user_image", filename, attachment_path, content, is_private=False)
        user.user_image = user_image.file_url
        user.save()
        frappe.db.commit()
        
        return response("Success", 201, user.as_dict())
    
    except Exception as error:
        return response("Internal Server Error", 500, None, error)

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
        employee_user = frappe.db.get_value("Employee", {"name": employee_id}, ["user_id"])

        if not employee_user:
            return response("Resource Not Found", 404, None, "No user found with {employee_id}".format(employee_id=employee_id))
        
        user_roles = frappe.get_roles(employee_user)
        
        return response("Success", 200, user_roles)
    except Exception as e:
        frappe.log_error(title="API User roles", message=frappe.get_traceback())

@frappe.whitelist()
def store_fcm_token(employee_id: str = None , fcm_token: str = None, device_os: str = None):
    try:
        if not employee_id:
            return response("Bad Request", 400, None, "employee_id required.")

        if not fcm_token:
            return response("Bad Request", 400, None, "fcm_token required.")

        if not device_os:
            return response("Bad Request", 400, None, "device_os required.")

        if not isinstance(employee_id, str):
            return response("Bad Request", 400, None, "employee_id must be of type str.")
    
        if not frappe.db.exists("Employee", employee_id):
            return response("Resource Not Found", 404, None, "No resource found with {employee_id}".format(employee_id = employee_id))

        employee = frappe.get_doc("Employee", employee_id)
            
        employee.fcm_token = fcm_token
        employee.device_os = device_os
        employee.save()
        frappe.db.commit()
        return response("Success", 201, employee.as_dict())

    except Exception as error:
        frappe.log_error(title="API FCM Token", message=frappe.get_traceback())
        return response("Internal Server Error", 500, None, error)