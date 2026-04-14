import frappe
from frappe.email.doctype.email_queue.email_queue import send_now
def after_insert(doc, event):
	"""
	Force push the email if the recipients is not more than 19 records
	:param doc:
	:param event:
	:return:
	"""
	if len(doc.recipients) < 20:
		# It will send the email immediately as Administrator to avoid permission issues
		with frappe.as_admin():
			doc.send()

def flush_emails():
    """
    This function flush emails not sent in queue
    :return:
    """
    delete_eid_emails()
    emails_in_queue = frappe.get_list('Email Queue', filters={'status': 'Not Sent'})
    
    # Wrap the entire loop in as_admin to reduce overhead and ensure permissions
    with frappe.as_admin():
        for row in emails_in_queue:
            try:
                send_now(name=row.name)
            except Exception:
                # Log error if needed, but keep the loop running
                pass
    
    frappe.db.commit()

def delete_eid_emails():
    """
    This function delete emails sent to employee ID
    :return:
    """
    frappe.db.sql("""
        DELETE FROM `tabEmail Queue`
        WHERE name IN (SELECT e.name FROM `tabEmail Queue` e JOIN `tabEmail Queue Recipient` r
        ON r.parent=e.name WHERE r.recipient LIKE '2%');
    """)
