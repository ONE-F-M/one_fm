import frappe
from frappe import _
from one_fm.api.api import get_user_roles

"""
List of fields allowed to be modified based on role mentioned.
PROJECTS_MANAGER_FIELD_MAP = ["status", "priority", "completed_by", "completed_on", "exp_start_date", "exp_end_date"]
PROJECTS_USER_FIELD_MAP = ["status", "priority", "completed_on"]
"""
USER_ALLOWED_STATUSES = ["Open", "Working", "Pending Review"]

def validate_task(doc, method):
    # Check user role and see if they have updated any values based on the field map. 
    roles = get_user_roles()
    if "Projects User" in roles and "Projects Manager" not in roles:
        validate_updated_fields(doc)

def validate_updated_fields(doc):
    if doc.has_value_changed('status'):
        if doc.status not in USER_ALLOWED_STATUSES:
            frappe.throw(_("Insufficient permission for updating status."))
    if doc.has_value_changed('priority') or doc.has_value_changed('completed_on'):
        frappe.throw(_("Insufficient permission for updating {0}").format("Priority" if doc.has_value_changed('priority') else 'Completed On'))
