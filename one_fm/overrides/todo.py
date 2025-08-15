import json
import frappe
from frappe.utils import get_fullname, get_url_to_form, getdate
from bs4 import BeautifulSoup
from datetime import datetime,timezone, timedelta
from one_fm.processor import is_user_id_company_prefred_email_in_employee, sendemail
from googleapiclient.discovery import build
from frappe import _
from google.oauth2 import service_account
from frappe.desk.doctype.todo.todo import ToDo as FrappeToDo

class ToDo(FrappeToDo):
    def on_trash(self):
        """Override trash to also close Google Task if present."""
        super().on_trash()
        try:
            delete_google_task_on_todo_delete(self)
        except Exception as e:
            frappe.log_error(message=f"Failed to delete Google Task on ToDo trash: {e}", title="ToDo on_trash Error")

def validate_todo(doc, method):
    notify_todo_status_change(doc)
    set_todo_type_from_refernce_doc(doc)
    validate_google_task_title(doc)

def notify_todo_status_change(doc):
    """Notify user if ToDo status changes. Modular, clear, and logs notification."""
    if doc.is_new():
        return
    status_in_db = frappe.db.get_value(doc.doctype, doc.name, "status")
    if status_in_db != doc.status and doc.assigned_by != doc.allocated_to:
        user = frappe.session.user
        subject, email_content = build_notification_subject_content(doc, user)
        create_notification_log(doc, user, subject, email_content)

def build_notification_subject_content(doc, user):
    """Builds subject and content for notification email."""
    subject = _("{0}({1}) assignment is {2}".format(doc.reference_type, doc.reference_name, doc.status))
    email_content = _(f"""
        The assignment referenced to {0}({1}) is {2} by {3}. See Details Below <br>
        <p>Description: {4} </p> <br>
        <p>Date of Allocation:{5}</p> <br>
        <p>Due Date:{6}</p> <br>
    """.format(doc.reference_type, doc.reference_name, doc.status, get_fullname(user), doc.description, doc.creation, doc.date))
    if doc.reference_type == "Task":
        task_subject = frappe.db.get_value("Task", doc.reference_name, "subject")
        subject = _('{0} "{1}"({2}) assignment is {3}'.format(doc.reference_type, task_subject, doc.reference_name, doc.status))
        email_content += f"<p>Subject:{task_subject}</p>"
    return subject, email_content

def create_notification_log(doc, user, subject, email_content):
    """Creates a notification log entry."""
    notification_log = frappe.new_doc("Notification Log")
    notification_log.subject = subject
    notification_log.email_content = email_content
    notification_log.for_user = doc.assigned_by
    notification_log.document_type = doc.doctype
    notification_log.document_name = doc.name
    notification_log.from_user = user
    notification_log.type = "Alert" if send_notification_alert_only(doc.assigned_by) else "Assignment"
    notification_log.insert(ignore_permissions=True)

def send_notification_alert_only(user):
    """Return True if only alert (not email) should be sent to user."""
    if user == "Administrator":
        return True
    if not is_user_id_company_prefred_email_in_employee(user):
        return True
    return False

def validate_google_task_title(doc):
    """Set a meaningful Google Task title for the ToDo if not already set."""
    if doc.custom_google_task_title:
        return
    if doc.reference_type == "Task" and doc.reference_name:
        doc.custom_google_task_title = frappe.db.get_value("Task", doc.reference_name, "subject")
    elif doc.reference_type and doc.reference_name:
        doc.custom_google_task_title = f"Action required for {doc.reference_type} - {doc.reference_name}"
    else:
        doc.custom_google_task_title = convert_html_to_plain_text(doc.description)[:100]

def set_todo_type_from_refernce_doc(doc):
    """Set the ToDo type from the referenced document, or default to 'Action'."""
    if not (doc.reference_type and doc.reference_name):
        return    
    if doc.reference_type in ["Project", "Task"]:
        meta = frappe.get_meta(doc.reference_type)
        if meta.has_field("type"):
            doc.type = frappe.db.get_value(doc.reference_type, doc.reference_name, "type")
            return
    doc.type = "Action"

def is_google_task_synchronization_enabled():
    return frappe.db.get_single_value("ONEFM General Setting", "google_task_synchronization_enabled")

def get_google_task_service(employee_email):
    """Return Google Tasks API service for the given employee email. Logs and returns None on error."""
    credentials_path = frappe.get_site_path("private", "files", "gcp.json")
    try:
        with open(credentials_path, "r") as file:
            credentials_dict = json.load(file)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict, scopes=["https://www.googleapis.com/auth/tasks"])
        delegated_credentials = credentials.with_subject(employee_email)
        return build("tasks", "v1", credentials=delegated_credentials)
    except Exception as e:
        frappe.log_error(title="Error reading Google credentials", message=str(e))
        return None

def before_save(doc,method):
    previous_doc = doc.get_doc_before_save()
    if previous_doc:
        service = get_google_task_service(previous_doc.allocated_to)
        return service

def create_google_task_on_todo_creation(doc, method):
    # Skip if general trigger is not enabled
    if not is_google_task_synchronization_enabled():
        return
    frappe.enqueue(create_google_task_on_todo_creation_in_erp(doc=doc, method=method),is_async=True)

def create_google_task_on_todo_creation_in_erp(doc, method):
    """Create a Google Task for the ToDo document if not already created."""
    employee_email = doc.allocated_to
    if doc.custom_google_task_id:
        return
    if not employee_email:
        frappe.throw(_("No assigned user found for this ToDo"))
    try:
        service = get_google_task_service(employee_email)
        if not service:
            frappe.log_error(message="Google Task service unavailable", title="Google Task Creation Error")
            return
        if method == "on_update":
            prev_service = before_save(doc, method)
            if doc.custom_google_task_id and prev_service:
                check_google_task_exists(doc.custom_google_task_id, prev_service)
        task_notes = create_description_for_google_todo(doc)
        task_title = doc.custom_google_task_title
        date_obj = datetime.strptime(str(doc.date), "%Y-%m-%d")
        due_date = date_obj.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).isoformat()
        task_body = {
            "title": task_title,
            "notes": task_notes,
            "due": due_date
        }
        result = service.tasks().insert(tasklist="@default", body=task_body).execute()
        doc.custom_google_task_id = result["id"]
        doc.save()
        return result
    except Exception as e:
        frappe.log_error(message=str(e), title=f"Error while creating Google Task from ToDo for {employee_email}")
    return

def check_google_task_exists(task_id,pev_emp_service=None):
    if pev_emp_service:
        task = pev_emp_service.tasks().get(tasklist="@default", task=task_id).execute()
        task["status"] = "completed"
        result = pev_emp_service.tasks().update(tasklist="@default",task=task_id, body=task).execute()


def create_description_for_google_todo(doc):
    """Generate a plain text description for Google Task from ToDo details."""
    try:
        task_notes = convert_html_to_plain_text(doc.description)
    except Exception:
        task_notes = doc.description
    if doc.reference_type and doc.reference_name:
        todo_reference = get_url_to_form("Todo", doc.name) if doc.name else ""
        todo_doc_type = doc.reference_type or ""
        todo_reference_link = get_url_to_form(todo_doc_type, doc.reference_name) if doc.reference_name else ""
        warning_msg = f"""
        Hey you can't update this task on Google Task, Close the task in ERPNext

        ToDo Reference: {todo_reference}
        Reference DocType: {todo_doc_type}
        Reference Name: {todo_reference_link}
        """
        if warning_msg not in task_notes:
            task_notes += warning_msg
    return task_notes

def convert_html_to_plain_text(html_content):
    """Convert HTML content to plain text for Google Task notes."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        text_output = "\n".join(paragraphs)
        table = soup.find("table")
        if not text_output and not table:
            return html_content
        if table:
            rows = table.find_all("tr")
            table_content = "\n".join(
                " : ".join(td.get_text(strip=True) for td in row.find_all('td')) for row in rows
            )
            text_output += "\n\nDetails:\n" + table_content + "\n"
        return text_output
    except Exception as e:
        frappe.log_error(message=str(e), title="Error converting HTML to plain text")
        return "Failed to parse content."


def update_google_task_on_todo_status_change(doc, method):
    """Update Google Task when ToDo status changes."""
    if doc.is_new() or not is_google_task_synchronization_enabled():
        return
    if not doc.custom_google_task_id:
        return
    employee_email = doc.allocated_to
    if not employee_email:
        frappe.throw(_("No assigned user found for this ToDo"))
    service = get_google_task_service(employee_email)
    if not service:
        frappe.log_error(message="Google Task service unavailable", title="Google Task Update Error")
        return
    try:
        task = service.tasks().get(tasklist="@default", task=doc.custom_google_task_id).execute()
    except Exception:
        task = create_google_task_on_todo_creation_in_erp(doc, method)
    if not task:
        frappe.log_error(title="Google task creation failed", message=f"Could not create Google Task for ToDo {doc.name}")
        return
    try:
        task_title = doc.custom_google_task_title
        task_notes = create_description_for_google_todo(doc)
        date_obj = datetime.strptime(str(doc.date), "%Y-%m-%d")
        due_date = date_obj.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).isoformat()
        task["title"] = task_title
        task["notes"] = task_notes
        task["due"] = due_date
        task["status"] = "needsAction" if doc.status == "Open" else "completed"
        service.tasks().update(tasklist="@default", task=doc.custom_google_task_id, body=task).execute()
    except Exception:
        frappe.log_error(title="Google Task Update Failed", message=frappe.get_traceback())

    
def delete_google_task_on_todo_delete(doc):
    if not doc.custom_google_task_id:
        return {"status": "skipped", "message": "No Google Task ID"}
    employee_email = getattr(doc, "allocated_to", None)
    if not employee_email:
        frappe.throw(_("No assigned user found for this ToDo"))
    result = {}
    if doc.custom_google_task_id:
        employee_email = doc.allocated_to
        if not employee_email:
            frappe.throw(_("No assigned user found for this ToDo"))
        try:
            service = get_google_task_service(employee_email)
            response = service.tasks().delete(tasklist="@default", task=doc.custom_google_task_id).execute()
            # Google Tasks API delete returns an empty dict on success
            if response == {}:
                result = {"status": "deleted"}
            else:
                result = {"status": "unknown", "response": response}
        except Exception as e:
            frappe.log_error(
                message=f"Failed to delete Google Task '{doc.custom_google_task_id}' for ToDo {doc.name}: {frappe.utils.get_traceback()}",
                title="Google Task Deletion Error"
            )
            result = {"status": "error", "message": f"Failed to delete Google Task: {e}"}
    return result

def get_mapped_status_from_google_task(task):
    """
        Map google task status to ERP ToDo status
    """
    if task.get("deleted"):
        return "Cancelled"
    if task.get("status") == "completed":
        return "Closed"
    return "Open"

@frappe.whitelist()
def sync_google_tasks_with_todos():
    try:
        # Skip if general trigger is not enabled
        if not is_google_task_synchronization_enabled():
            return

        active_users = frappe.get_all("User", {"enabled": 1})
        user_emails_having_google_account = [user.name for user in active_users if is_user_id_company_prefred_email_in_employee(user.name)]

        # Batching user emails in group of 5
        batch_size = 5
        for i in range(0, len(user_emails_having_google_account), batch_size):
            batch_user_emails = user_emails_having_google_account[i:i+batch_size]
            frappe.enqueue(sync_google_tasks_for_users, user_emails=batch_user_emails, is_async=True)

        return { "error": False, "message" : "Google Tasks synchronized successfully" }

    except Exception as e:
        frappe.log_error(message = str(e),title =  "Failed to sync google tasks to ERP ToDo")
        return { "error": True, "message" : str(e) }


@frappe.whitelist()
def sync_my_google_tasks_with_todos():
    try:
        logged_in_user = frappe.session.user

        # Skip if general trigger is not enabled
        if not is_google_task_synchronization_enabled() or logged_in_user == "Administrator":
            return { "error": True, "message" : "You are not allowed to sync google tasks" }

        sync_google_tasks_for_users(user_emails=[logged_in_user])

        return { "error": False, "message" : "My Google Tasks synchronized successfully" }

    except Exception as e:
        frappe.log_error(message =str(e),title = "Failed to sync google tasks to ERP ToDo")
        return { "error": True, "message" : str(e) }


@frappe.whitelist()
def sync_google_tasks_for_users(user_emails=[]):
    all_google_tasks = []

      # Iterate through user emails having google account and fetch each user's tasks
    for user_email in user_emails:
        try:
            service = get_google_task_service(user_email)

            five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
            updated_min = five_minutes_ago.isoformat()

            results = service.tasks().list(tasklist="@default", showHidden=True, showDeleted=True, updatedMin=updated_min).execute()
            user_tasks = results.get("items", [])

            # Append user_email to each google_task for later use in allocated_to field
            for task in user_tasks:
                task["user_email"] = user_email

            all_google_tasks.extend(user_tasks)
        except Exception as e:
            frappe.log_error(message=str(e), title=f"Failed to fetch tasks for user {user_email}")

    # Iterate through all Google tasks and sync them to ERP ToDo
    for google_task in all_google_tasks:
        try:
            google_task_id = google_task["id"]

            todos = frappe.get_all("ToDo", filters={"custom_google_task_id": google_task_id}, limit=1)

            due_date_str = google_task.get("due", None)
            due_date = getdate(due_date_str) if due_date_str else None
            task_title = google_task.get("title", "")[:100]
            task_description = google_task.get("notes", "") or google_task.get("title", "")
            allocated_to = google_task.get("user_email", "")
            mapped_status = get_mapped_status_from_google_task(google_task)

            if todos:
                # If ToDo already exists
                todo = frappe.get_doc("ToDo", todos[0]["name"])
                todo.db_set("description", task_description)
                todo.db_set("custom_google_task_title", task_title)
                todo.db_set("date", due_date)
                todo.db_set("allocated_to", allocated_to)

                # If status doesnot match
                if mapped_status != todo.status:
                    # If ToDo has any reference then it shouldn't be closed by Google Task
                    if todo.reference_type and google_task.get("status") == "completed" and todo.status not in ["Closed", "Cancelled"]:
                        service = get_google_task_service(allocated_to)
                        payload = {
                            **google_task,
                            "title": f"[Hey!! You cant do that, Close the task in ERPNext] - {task_title}",
                            "status": "needsAction"
                        }
                        service.tasks().update(tasklist="@default",task=google_task_id, body=payload).execute()
                    else:
                        todo.db_set("status", mapped_status)
            else:
                # If ToDo doesn't exist, create a new ToDo with google task details
                new_todo = frappe.get_doc({
                    "doctype": "ToDo",
                    "description": task_description,
                    "date": due_date,
                    "status": mapped_status,
                    "custom_google_task_title": task_title,
                    "custom_google_task_id": google_task_id,
                    "allocated_to": allocated_to,
                    "custom_source": "Google Task"
                })
                new_todo.insert(ignore_permissions=True)

        except Exception as e:
            frappe.log_error(message = str(e),title = f"Failed to sync Google task {google_task_id} to ERP ToDo")

@frappe.whitelist()
def send_email_on_todo_created(doc, method):
    if not doc.notify_allocated_to_via_email:
        return
    user_id = frappe.session.user
    user_email = frappe.db.get_value("User", user_id, "email")
    if user_email == doc.allocated_to:
        return
    recipients = [doc.allocated_to]
    todo_reference = ""
    todo_doc_type = ""
    todo_reference_link = ""
    if doc.reference_type and doc.reference_name:
        todo_reference = get_url_to_form("Todo", doc.name)
        todo_doc_type = doc.reference_type
        todo_reference_link = get_url_to_form(todo_doc_type, doc.reference_name)
    args = frappe._dict({
                    "task_id": doc.custom_google_task_id,
                    "source": doc.custom_source,
                    "task_title": doc.custom_google_task_title,
                    "name":doc.name,
                    "todo_reference": todo_reference,
                    "todo_doc_type":todo_doc_type,
                    "description":doc.description,
                    "reference_name":doc.reference_name,
                    "todo_reference_link":todo_reference_link,
                    "due_date":doc.date,
                    "status" : doc.status,
                })

    message = frappe.render_template("one_fm/templates/emails/email_notification_on_task_creation.html", args)
    subject = f"""A Task has been Created via {doc.custom_source} by {user_id}"""
    sendemail(recipients= recipients, message=message, subject=subject)