import frappe
from frappe.desk.doctype.notification_log.notification_log import *
from frappe.utils.data import get_url_to_form, strip_html

from one_fm.processor import sendemail


class NotificationLogOverride(NotificationLog):
    def after_insert(self):
        frappe.publish_realtime("notification", after_commit=True, user=self.for_user)
        set_notifications_as_unseen(self.for_user)
        if is_email_notifications_enabled_for_type(self.for_user, self.type):
            try:
                custom_send_notification_email(self)
            except frappe.OutgoingEmailError:
                self.log_error(_("Failed to send notification email"))
                
                

def custom_send_notification_email(doc):
    if doc.type == "Energy Point" and doc.email_content is None:
        return

    email = frappe.db.get_value("User", doc.for_user, "email")
    if not email:
        return

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
   
    
	



