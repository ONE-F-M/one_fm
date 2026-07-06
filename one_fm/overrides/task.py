import frappe
from frappe import _
from one_fm.api.api import get_user_roles
from frappe.desk.form.assign_to import get as get_assignments,add as add_assignment, remove as remove_assignment
from erpnext.projects.doctype.task.task import Task

USER_ALLOWED_STATUSES = ["Open", "Working", "Pending Review"]

class TaskOverride(Task):
    def validate(self):
        super(TaskOverride, self).validate()
        validate_task(self)

    def after_insert(self):
        after_task_insert(self)



def validate_task(doc):
    # Re-enabled: project_task_lifecycle only syncs custom_assigned_to once,
    # at creation ("Sync Assigned To -> Create ToDo(s)") — a User Task
    # already Waiting doesn't re-resolve assignees mid-wait. This keeps ToDo
    # visibility correct if someone edits custom_assigned_to while a task is
    # already Accepted/under review. Note: the BPMN engine's own
    # authorization for who can complete a User Task was locked in when that
    # task started, so a newly-added assignee here may see a ToDo before
    # they're actually able to act on it — catches up on the next loop-back
    # (Return -> Accept or Cancel Task) when the engine re-resolves fresh.
    if not doc.is_new() and doc.workflow_state in ["Open", "Working"]:
        # sync_assign_to_field(doc) # Handled by project_task_lifecycle.bpmn Event-Based Gateway
        pass

    # Cancel assignee ToDos on entering Pending Review — now handled by the
    # BPMN engine itself: when the "Submit for Review" User Task completes,
    # _sync_active_tasks() diffs prev/curr assignees and closes the ToDo for
    # everyone who was on that task (remove_frappe_assignment), same doc.name
    # scope as below. One difference: the engine sets ToDo status "Closed",
    # this code set "Cancelled" — same practical effect (no longer open).
    # all_asssigned_users = doc.get_assigned_users()
    # assignees = doc.custom_assigned_to
    # if doc.workflow_state == "Pending Review" and assignees:
    #     for assignee in assignees:
    #         if assignee.user in list(all_asssigned_users):
    #             todos = frappe.get_all(
    #                 "ToDo",
    #                 filters={
    #                     "reference_type": doc.doctype,
    #                     "reference_name": doc.name,
    #                     "allocated_to": assignee.user,
    #                     "status": ["!=", "Closed"]  # only update if not already closed
    #                 },
    #                 pluck="name"
    #             )
    #             if todos:
    #                 frappe.db.set_value("ToDo", {"name": ["in", todos]}, "status", "Cancelled")

    # Restored: Python is back in control of who may hand-edit status/
    # priority/completed_on (Manager Override + the DocType-level field lock
    # were reverted). Projects Manager (or a project's own manager) keeps the
    # same direct-edit exemption it always had.
    #
    # bpmn_engine_action exemption kept: Apply Workflow's own doc.save() for
    # the normal Accept/Submit/Confirm/Return flow runs as self._initiated_by
    # (the task's creator), not the person who actually clicked the action —
    # without this, a Task created by a plain "Projects User" on a project
    # would have the engine's own Confirm/Cancel step blocked the moment it
    # tries to reach "Completed"/"Cancelled" (neither is in
    # USER_ALLOWED_STATUSES), even though nothing about that transition was
    # actually a manual edit.
    if not getattr(frappe.flags, "bpmn_engine_action", False):
        roles = get_user_roles()
        is_manager = is_project_manager(doc.project) if doc.project else False
        if "Projects User" in roles and "Projects Manager" not in roles and not is_manager and (doc.project or doc.owner != frappe.session.user):
            validate_updated_fields(doc)

    # NOT covered by processa — no step in the diagram sets completed_on/
    # completed_by. Still needed: Apply Workflow's doc.save() re-enters this
    # validate() hook, so this keeps firing correctly now that `status` is
    # kept in sync by the diagram's Update Field steps.
    # check_completed_by_and_completed_on(doc) # Handled by project_task_lifecycle.bpmn Update Field tasks
    pass

def after_task_insert(doc):
    # Now handled by project_task_lifecycle: the Conditional Start Event
    # (Task / After Insert) fires "Sync Assigned To -> Create ToDo(s)",
    # which runs the same reconciliation as sync_assign_to_field() below.
    # sync_assign_to_field(doc)
    pass


def check_completed_by_and_completed_on(doc):
    pass
    # if doc.status == "Pending Review" or doc.status=="Completed":
    #     if not doc.completed_on or doc.completed_on != frappe.utils.nowdate():
    #         doc.completed_on = frappe.utils.nowdate()
    #     if doc.custom_assigned_to:
    #         if not doc.completed_by or doc.completed_by!=doc.custom_assigned_to[0].user:
    #             doc.completed_by = doc.custom_assigned_to[0].user

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
