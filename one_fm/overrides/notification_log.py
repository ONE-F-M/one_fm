import frappe
from frappe.desk.doctype.notification_log.notification_log import *
from frappe.utils.data import get_url_to_form, strip_html
from frappe import _

from one_fm.processor import sendemail


class NotificationLogOverride(NotificationLog):
    def after_insert(self):
        # Skip notification entirely for non-Action ToDo assignments.
        # Processa handles notifications for Process-type tasks independently.
        if self.type == "Assignment" and self._is_non_action_todo_assignment():
            return

        frappe.publish_realtime("notification", after_commit=True, user=self.for_user)
        set_notifications_as_unseen(self.for_user)
        if is_email_notifications_enabled_for_type(self.for_user, self.type):
            try:
                custom_send_notification_email(self)
            except frappe.OutgoingEmailError:
                frappe.log_error(frappe.get_traceback(), _("Failed to send notification email"))
            except Exception:
                # Never let email failures block workflow transitions, but distinctly log them
                frappe.log_error(frappe.get_traceback(), "Notification Email Failed (non-blocking)")

    def _is_non_action_todo_assignment(self):
        """Return True if this Assignment notification is for a non-Action ToDo.

        Looks up the open ToDo that matches the notification's document and
        recipient. If the ToDo has a type explicitly set to something other
        than "Action" (e.g. "Process"), the standard notification is skipped.
        Empty/None type is treated as "Action" (the default).
        """
        if not (self.document_type and self.document_name and self.for_user):
            return False

        todo_type = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": self.document_type,
                "reference_name": self.document_name,
                "allocated_to": self.for_user,
                "status": "Open",
            },
            "type",
        )
        return bool(todo_type and todo_type != "Action")


def custom_send_notification_email(doc):
    if doc.type == "Energy Point" and doc.email_content is None:
        return

    email = frappe.db.get_value("User", doc.for_user, "email")
    if not email:
        return

    if doc.document_type == "HD Ticket":
        doc_link = frappe.utils.get_url(f"/helpdesk/tickets/{doc.document_name}")
    else:
        doc_link = get_url_to_form(doc.document_type, doc.document_name)
    header = get_email_header(doc)
    email_subject = strip_html(doc.subject)
    context = {
			"body_content": doc.subject,
			"description": doc.email_content,
			"document_type": doc.document_type,
			"document_name": doc.document_name,
			"doc_link": doc_link,
            "header": header
		}
    
    msg = frappe.render_template('one_fm/templates/emails/notification_log.html', context=context)

    sendemail(recipients=email,content=msg, subject=email_subject)
