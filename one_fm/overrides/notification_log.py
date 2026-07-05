import frappe
from frappe.desk.doctype.notification_log.notification_log import *
from frappe.utils.data import get_url_to_form, strip_html
from frappe import _

from one_fm.processor import sendemail


class NotificationLogOverride(NotificationLog):
    def after_insert(self):
        if self.type == "Assignment":
            todo = self._get_matching_todo()
            # Skip notification entirely for non-Action ToDo assignments.
            # Processa handles notifications for Process-type tasks independently.
            if self._is_non_action_todo_assignment(todo):
                return
            # Skip the "... has been removed by ..." email when the un-assignment
            # was driven by an assignment rule re-running on a workflow transition
            # (i.e. reassignment noise). Manual UI removals still notify.
            if self._is_assignment_rule_removal(todo):
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

    def _get_matching_todo(self):
        """Return the most recently modified ToDo matching this notification.

        Status is intentionally NOT filtered: removal/close notifications
        ("... has been removed by ...") are created *after* `set_status` has
        already flipped the ToDo to Cancelled/Closed, so an "Open"-only lookup
        would miss them. Returns a dict with `type`, `status` and
        `assignment_rule`, or None if no ToDo matches.
        """
        if not (self.document_type and self.document_name and self.for_user):
            return None

        todo = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": self.document_type,
                "reference_name": self.document_name,
                "allocated_to": self.for_user,
            },
            fields=["type", "status", "assignment_rule"],
            order_by="modified desc",
            limit=1,
        )
        return todo[0] if todo else None

    def _is_non_action_todo_assignment(self, todo=None):
        """Return True if this Assignment notification is for a non-Action ToDo.

        If the ToDo has a type explicitly set to something other than "Action"
        (e.g. "Process"), the standard notification is skipped. Empty/None type
        is treated as "Action" (the default).
        """
        todo_type = todo.type if todo else None
        return bool(todo_type and todo_type != "Action")

    def _is_assignment_rule_removal(self, todo=None):
        """Return True if this is a removal notification for a rule-driven ToDo.

        When a workflow transition re-runs the assignment rules, the previous
        state's rule un-assigns its ToDo (status -> Cancelled/Closed), and
        Frappe core unconditionally emails the assignee "... has been removed
        by ...". That email is pure reassignment noise. We detect it by the
        ToDo being Cancelled/Closed AND carrying an `assignment_rule` (manual
        UI removals have no `assignment_rule`, so they are left untouched).
        """
        if not todo:
            return False
        return bool(todo.assignment_rule) and todo.status in ("Cancelled", "Closed")


def custom_send_notification_email(doc):
    if doc.type == "Energy Point" and doc.email_content is None:
        return

    email = frappe.db.get_value("User", doc.for_user, "email")
    if not email:
        return

    if doc.document_type == "HD Ticket":
        doc_link = frappe.utils.get_url(f"/helpdesk/tickets/{doc.document_name}")
    elif doc.document_type == "BPMN Process Model" and doc.link:
        doc_link = frappe.utils.get_url(f"{doc.link}")
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
