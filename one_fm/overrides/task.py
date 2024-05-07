import frappe
from frappe import _
from one_fm.api.api import get_user_roles

"""
List of fields allowed to be modified based on role mentioned.
PROJECTS_MANAGER_FIELD_MAP = ["status", "priority", "completed_by", "completed_on", "exp_start_date", "exp_end_date"]
PROJECTS_USER_FIELD_MAP = ["status", "completed_by", "exp_start_date", "exp_end_date"]
"""
USER_ALLOWED_STATUSES = ["Open", "Working", "Pending Review"]

def validate_task(doc, method):
    roles = get_user_roles()
    is_manager = is_project_manager(doc.project) if doc.project else False
    if "Projects User" in roles and "Projects Manager" not in roles and not is_manager:
        validate_updated_fields(doc)

def validate_updated_fields(doc):
    if doc.has_value_changed('status'):
        if doc.status not in USER_ALLOWED_STATUSES:
            frappe.throw(_("Insufficient permission for updating status."))
    if not doc.is_new() and (doc.has_value_changed('priority') or doc.has_value_changed('completed_on')):
        frappe.throw(_("Insufficient permission for updating {0}").format("Priority" if doc.has_value_changed('priority') else 'Completed On'))

def is_project_manager(project):
    project_manager = frappe.get_value("Project", project, "account_manager")
    project_users = frappe.get_all("Project User",{'parent':project},['user'])
    user_employee = frappe.get_value("Employee", {"user_id": frappe.session.user}) if frappe.db.exists("Employee", {"user_id": frappe.session.user}) else None

    if user_employee and project_manager and user_employee == project_manager:
        return True
    if project_users:
        all_users = [i.user for i in project_users]
        if frappe.session.user in all_users:
            return True
    return False


@frappe.whitelist()
def get_roles_and_validate_is_manager(project=None):
    roles = get_user_roles()
    is_manager = is_project_manager(project) if project else False
    return roles, is_manager