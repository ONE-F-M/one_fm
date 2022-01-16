import frappe
import base64
from one_fm.api.v1.utils import response

@frappe.whitelist()
def get_user_details(user_id: str = None):

    if not user_id:
        return response("Bad request", 400, None, "employee_id required.")

    if not isinstance(user_id, str):
        return response("Bad request", 400, None, "employee_id must be of type str.")

    try:
        user = frappe.get_value("User", user_id, ["*"])
        
        if not user:
            return response("REsource not found", 404, None, "No resource found with {user_id}".format(user_id = user_id))
        
        employee, designation = frappe.get_value("Employee", { "user_id": user_id }, ["name", "designation"])

        user_details = {}
        user_details.name = user.full_name
        user_details.email = user.email
        user_details.mobile_no = user.mobile_no
        user_details.designation = designation
        user_details.employee = employee
        user_details.user_image = user.user_image

        return response("Success", 200, user_details)
    
    except Exception as error:
        return response("Internal server error", 500, None, error)

@frappe.whitelist()
def change_user_profile_image(user_id: str = None, image: str = None):

    if not user_id:
        return response("Bad request", 400, None, "user_id required.")

    if not isinstance(user_id, str):
        return response("Bad request", 400, None, "user_id must be of type str.")

    if not image:
        return response("Bad request", 400, None, "image required.")

    if not isinstance(image, str):
        return response("Bad request", 400, None, "image must be of type str.")
    
    content = base64.b64decode(image)
    filename = user_id + ".png"
    
    OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/public/files/ProfileImage/"+filename
    fh = open(OUTPUT_IMAGE_PATH, "wb")
    fh.write(content)
    fh.close()
    
    image_file="/files/ProfileImage/"+filename
    
    try:
        user = frappe.get_doc("User", user_id)

        if not user:
            return response("Resource not found", 404, None, "No resource found with {user_id}".format(user_id = user_id))

        user.user_image = image_file
        user.save()
        frappe.db.commit()
        
        return response("Success", 201, user.as_dict())
    
    except Exception as error:
        return response("Internal server error", 500, None, error)

@frappe.whitelist()
def get_user_roles(user_id: str = None):
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
    
    user_roles = frappe.get_roles(user_id)
    
    return response("Success", 200, user_roles)

@frappe.whitelist()
def store_fcm_token(employee_id: str = None , fcm_token: str = None, device_os: str = None):
    if not employee_id:
        return response("Bad request", 400, None, "employee_id required.")

    if not fcm_token:
        return response("Bad request", 400, None, "fcm_token required.")

    if not device_os:
        return response("Bad request", 400, None, "device_os required.")

    if not isinstance(employee_id, str):
        return response("Bad request", 400, None, "employee_id must be of type str.")
    
    employee = frappe.get_doc("Employee", {"name": employee_id})
    
    if not employee:
        return response("Resource not found", 404, None, "No resource found with {user_id}".format(employee_id = employee_id))
    
    try:
        employee.fcm_token = fcm_token
        employee.device_os = device_os
        employee.save()
        frappe.db.commit()
        return response("Success", 201, employee.as_dict())

    except Exception as error:
        return response("Internal server error", 500, None, error)