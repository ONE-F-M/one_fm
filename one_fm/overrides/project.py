import frappe
from frappe.core.doctype.version.version import get_diff
from frappe.desk.form.assign_to import add as assign, DuplicateToDoError, remove as remove_assignment
from frappe import _
from frappe.utils import getdate
from one_fm.api.doc_events import update_project_manager_name, on_project_update_switch_shift_site_post_to_inactive
from one_fm.processor import sendemail
from one_fm.one_fm.project_custom import validate_poc_list, validate_project, get_depreciation_expense_amount

from erpnext.projects.doctype.project.project import Project


def notify_project_team(doc):
    template = "one_fm/templates/emails/notify_project_manager.html"
    
    if not doc.project_manager:
        return
    project_manager = frappe.get_doc("Employee", doc.project_manager)
    project_manager_name = project_manager.employee_name
    project_manager_email = project_manager.user_id
    project_team = []
    for user in doc.users:
        project_team.append({
            "full_name": user.full_name,
            "contact": user.email,
        })
    recipient = [project_manager_email]
    subject = _("New Project Assignment: {0}").format(doc.project_name)
   
    msg = frappe.render_template(template, {
        "project_name": doc.project_name,
        "start_date": doc.expected_start_date,
        "end_date": doc.expected_end_date,
        "project_manager_name": project_manager_name,
        "project_outcome": doc.custom_project_outcome,
        "success_completion_criteria": doc.custom_success_and_completion_criteria,
        "success_metrics":doc.custom_success_metrics,
        "project_team": project_team,
    })
    secondary_recipients = [user.email for user in doc.users if user.email]
    secondary_msg = frappe.render_template("one_fm/templates/emails/notify_project_team.html", {
        "project_name": doc.project_name,
        "start_date": doc.expected_start_date,
        "end_date": doc.expected_end_date,
        "project_manager_name": project_manager_name,
        "team_member": "{{ full_name }}",
        "project_outcome": doc.custom_project_outcome,
        "success_completion_criteria": doc.custom_success_and_completion_criteria,
        "success_metrics":doc.custom_success_metrics,
        'project_team': project_team,
    })
    if secondary_recipients:
        sendemail(recipients=secondary_recipients, subject=subject, content=secondary_msg, is_scheduler_email=True)
        # frappe.enqueue(method=sendemail, queue="short", recipients=secondary_recipients, subject=subject, content=secondary_msg, is_scheduler_email=True)
    sendemail(recipients=recipient, subject=subject, content=msg, is_scheduler_email=True)
    # frappe.enqueue(method=sendemail, queue="short", recipients=recipient, subject=subject, content=msg, is_scheduler_email=True)
    

def update_project_user_assignment(doc, method):
    last_doc = doc.get_doc_before_save()
    
    if not last_doc: #new document
        assign_users_to_project(doc)
        notify_project_team(doc)
    else:
        added_users, removed_users = get_changed_users(doc)
        if added_users:
            for user in added_users:
                add_assignment(user, doc.name)
        if removed_users:
            for user in removed_users:
                remove_assignment("Project", doc.name, user)

def assign_users_to_project(doc):
    for user in doc.users:
        add_assignment(user.user, doc.name)
    if doc.project_manager:
        project_manager_id = frappe.get_value("Employee", doc.project_manager, "user_id")
        add_assignment(project_manager_id, doc.name)

def add_assignment(user, project):
    try:
        assign({
            "doctype": "Project",
            "name": project,
            "assign_to": [user],
            "description": _("The project is assigned to you.")
        })
    except DuplicateToDoError:
        frappe.message_log.pop()
        pass

def get_changed_users(project):
    project_before_save = project.get_doc_before_save()
    if project_before_save is None:
        return [], []
    changes = get_diff(project_before_save, project, for_child=True)

    user_change = next((c for c in changes.changed if c[0] == "users"), None)
    if not user_change:
        return [], []

    old_value, new_value = user_change[1], user_change[2]
    old_users = [user.user for user in old_value]
    new_users = [user.user for user in new_value]

    added_users = list(set(new_users) - set(old_users))
    removed_users = list(set(old_users) - set(new_users))

    return added_users, removed_users



class ProjectOverride(Project):
     
    def validate(self):
        if not self.is_new():
            self.copy_from_template()
        self.update_costing()
        self.update_percent_complete()
        self.validate_expected_dates()
        self.validate_from_to_dates("actual_start_date", "actual_end_date")
        validate_poc_list(self, None)
        validate_project(self, None)

    def validate_expected_dates(self):
        """Validate Expected Start/End Date, but only when this save touches them.

        `expected_start_date` / `expected_end_date` are read-only for External
        projects (see one_fm/custom/property_setter/project.py) and are written by
        Contracts through `db.set_value`. An inverted pair that is already stored
        therefore cannot be repaired from the form, and an unconditional throw here
        would block every unrelated edit on the project (e.g. changing the Project
        Manager) for good. So the hard validation applies to new documents and to
        saves that actually change a date; stored legacy values only warn.
        """
        dates_changed = (
            self.is_new()
            or self.has_value_changed("expected_start_date")
            or self.has_value_changed("expected_end_date")
        )

        if dates_changed:
            self.validate_from_to_dates("expected_start_date", "expected_end_date")
            return

        if (
            self.expected_start_date
            and self.expected_end_date
            and getdate(self.expected_end_date) < getdate(self.expected_start_date)
        ):
            # Non-blocking: the user cannot fix these fields here. They are corrected
            # on the linked Contracts record, which re-syncs the project.
            frappe.msgprint(
                _("Expected End Date is before Expected Start Date on this project. Please correct the dates on the linked contract."),
                indicator="orange",
                alert=True
            )

    def after_insert(self):
        super().after_insert()
        update_project_user_assignment(self, None)
    def onload(self):
        super().onload()
        get_depreciation_expense_amount(self)

    def on_update(self):
        update_project_manager_name(self, None)
        on_project_update_switch_shift_site_post_to_inactive(self, None)