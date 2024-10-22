import frappe
from frappe import _
from one_fm.api.api import get_user_roles
from frappe.desk.form.assign_to import get as get_assignments,add as add_assignment, remove as remove_assignment

"""
List of fields allowed to be modified based on role mentioned.
PROJECTS_MANAGER_FIELD_MAP = ["status", "priority", "completed_by", "completed_on", "exp_start_date", "exp_end_date"]
PROJECTS_USER_FIELD_MAP = ["status", "completed_by", "exp_start_date", "exp_end_date"]
"""
USER_ALLOWED_STATUSES = ["Open", "Working", "Pending Review"]

def validate_task(doc, method):
    # When new doc is added, then sync field after insert
    if not doc.is_new():
        sync_assign_to_field(doc)

    roles = get_user_roles()
    is_manager = is_project_manager(doc.project) if doc.project else False
    if "Projects User" in roles and "Projects Manager" not in roles and not is_manager and (doc.project or doc.owner != frappe.session.user):
        validate_updated_fields(doc)

def after_task_insert(doc, method):
    sync_assign_to_field(doc)

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

def sync_assign_to_field(doc):
    existing_doc_assignments = set([assignment.owner for assignment in get_assignments({'doctype': doc.doctype,'name': doc.name})])
    current_field_assignments = set([assignment.user for assignment in doc.custom_assigned_to])
    
    assignments_to_be_removed = list(existing_doc_assignments - current_field_assignments)
    assignments_to_be_added = list(current_field_assignments - existing_doc_assignments)

    # Remove assignments for users who are not added in "Assigned To" (Custom Field)
    for user in assignments_to_be_removed:
        remove_assignment(doc.doctype, doc.name, user)

    # Add assignments for users who are newly added in "Assigned To" (Custom Field)
    add_assignment({
                'assign_to': assignments_to_be_added,
                'doctype': doc.doctype,
                'name': doc.name,
                'description': doc.description,
            })


@frappe.whitelist()
def get_roles_and_validate_is_manager(project=None):
    roles = get_user_roles()
    is_manager = is_project_manager(project) if project else False
    return roles, is_manager