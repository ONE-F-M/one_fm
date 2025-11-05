import frappe
from one_fm.processor import is_user_id_company_prefred_email_in_employee
from one_fm.overrides.todo import sync_google_tasks_for_users

def execute():
    """
    Sync Google Tasks that were updated in the last 7 days with ERPNext ToDos.
    """
    if not frappe.db.get_single_value("ONEFM General Setting", "google_task_synchronization_enabled"):
        return

    active_users = frappe.get_all("User", {"enabled": 1})
    user_emails_having_google_account = [
        user.name for user in active_users if is_user_id_company_prefred_email_in_employee(user.name)
    ]

    if user_emails_having_google_account:
        sync_google_tasks_for_users(
            user_emails=user_emails_having_google_account,
            timedelta_kwargs={"days": 7}
        )
