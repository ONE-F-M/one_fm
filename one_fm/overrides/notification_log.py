import frappe
from frappe.desk.doctype.notification_log.notification_log import *
from frappe.utils.data import get_url_to_form, strip_html
from frappe import _

from one_fm.processor import sendemail


class NotificationLogOverride(NotificationLog):
    def after_insert(self):
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
                
                

def custom_send_notification_email(doc):
    if doc.type == "Energy Point" and doc.email_content is None:
        return

    email = frappe.db.get_value("User", doc.for_user, "email")
    if not email:
        return

    if doc.document_type == "HD Ticket":
        doc_link = frappe.utils.get_url(f"/helpdesk/tickets/{doc.name}")
    else:
        doc_link = doc.link or get_url_to_form(doc.document_type, doc.name)
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
