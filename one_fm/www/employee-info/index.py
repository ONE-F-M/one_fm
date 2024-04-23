import frappe
from datetime import datetime

def get_context(context):
    user_roles = frappe.get_user().get_roles()
    allowed_roles = get_allowed_roles()

    # Check if user has one of the allowed roles
    if not any(role in user_roles for role in allowed_roles):
        frappe.local.flags.redirect_location = '/'
        raise frappe.Redirect

    employee_id = frappe.form_dict.employee_id
    employee_details = frappe.get_doc("Employee", {'name': employee_id})
    employee_details.age = calculate_age(employee_details.date_of_birth)        
    context.employee = employee_details

def get_allowed_roles():
    try:
        general_setting = frappe.get_single("ONEFM General Setting")
        allowed_roles = []

        if general_setting.employee_info_access:
            for entry in general_setting.employee_info_access:
                allowed_roles.append(entry.role)

        return allowed_roles
    except Exception:
        return []

def calculate_age(birthdate):
    today = datetime.now().date()
    birthdate = datetime.strptime(str(birthdate), '%Y-%m-%d').date()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age
