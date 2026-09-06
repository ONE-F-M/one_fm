import frappe
from frappe import _
from one_fm.api.api import get_user_roles
from frappe.desk.form.assign_to import get as get_assignments,add as add_assignment, remove as remove_assignment
from erpnext.projects.doctype.task.task import Task

"""
List of fields allowed to be modified based on role mentioned.
PROJECTS_MANAGER_FIELD_MAP = ["status", "priority", "completed_by", "completed_on", "exp_start_date", "exp_end_date"]
PROJECTS_USER_FIELD_MAP = ["status", "completed_by", "exp_start_date", "exp_end_date"]
"""
USER_ALLOWED_STATUSES = ["Open", "Working", "Pending Review"]

class TaskOverride(Task):
    def validate(self):
        super(TaskOverride, self).validate()
        validate_task(self)

    def after_insert(self):
        after_task_insert(self)



def validate_task(doc):
    # When new doc is added, then sync field after insert
    if not doc.is_new() and doc.workflow_state in ["Open", "Working"]:
        sync_assign_to_field(doc)


    all_asssigned_users = doc.get_assigned_users()
    assignees = doc.custom_assigned_to
    if doc.workflow_state == "Pending Review" and assignees:
        for assignee in assignees:
            if assignee.user in list(all_asssigned_users):
                todos = frappe.get_all(
                    "ToDo",
                    filters={
                        "reference_type": doc.doctype,
                        "reference_name": doc.name,
                        "allocated_to": assignee.user,
                        "status": ["!=", "Closed"]  # only update if not already closed
                    },
                    pluck="name"
                )
                if todos:
                    frappe.db.set_value("ToDo", {"name": ["in", todos]}, "status", "Cancelled")

    roles = get_user_roles()
    is_manager = is_project_manager(doc.project) if doc.project else False
    # The task's reviewer and its assignees are the legitimate actors for the Task
    # workflow (assignees move Open -> Working -> Pending Review; the reviewer Confirms
    # to Completed or Returns to Open). The status/field restriction below is meant for a
    # Projects User who is a stranger to the task, so it must not block these actors.
    assignees = [d.user for d in (doc.custom_assigned_to or [])]
    is_task_actor = frappe.session.user == doc.custom_reviewer or frappe.session.user in assignees
    if (
        "Projects User" in roles
        and "Projects Manager" not in roles
        and not is_manager
        and not is_task_actor
        and (doc.project or doc.owner != frappe.session.user)
    ):
        validate_updated_fields(doc)

    check_completed_by_and_completed_on(doc)

def after_task_insert(doc):
    sync_assign_to_field(doc)


def check_completed_by_and_completed_on(doc):
    if doc.status == "Pending Review" or doc.status=="Completed":
        if not doc.completed_on or doc.completed_on != frappe.utils.nowdate():
            doc.completed_on = frappe.utils.nowdate()
        if doc.custom_assigned_to:
            if not doc.completed_by or doc.completed_by!=doc.custom_assigned_to[0].user:
                doc.completed_by = doc.custom_assigned_to[0].user

def validate_updated_fields(doc):
    if doc.has_value_changed('status'):
        if doc.status not in USER_ALLOWED_STATUSES:
            frappe.throw(_("Insufficient permission for updating status."))
    if not doc.is_new() and (doc.has_value_changed('priority') or doc.has_value_changed('completed_on')):
        frappe.throw(_("Insufficient permission for updating {0}").format("Priority" if doc.has_value_changed('priority') else 'Completed On'))

def is_project_manager(project):
    project_manager = frappe.get_value("Project", project, "project_manager")
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
    existing_doc_assignments = set([assignment.owner for assignment in get_assignments({'doctype': doc.doctype,'name': doc.name}) if assignment.owner])
    current_field_assignments = set([assignment.user for assignment in doc.custom_assigned_to if assignment.user])

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
                'description': doc.subject,
            })


@frappe.whitelist()
def get_roles_and_validate_is_manager(project=None):
    roles = get_user_roles()
    is_manager = is_project_manager(project) if project else False
    return roles, is_manager
