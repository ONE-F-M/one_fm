import frappe
from frappe.email.doctype.email_queue.email_queue import send_now
def after_insert(doc, event):
	"""
	Force push the email if the recipients is not more than 19 records
	:param doc:
	:param event:
	:return:
	"""
	found = True
	if len(doc.recipients) >= 20:
		found = False
	if found:
		# It will send the email immediately
		doc.send()

def flush_emails():
    """
    This function flush emails not sent in queue
    :return:
    """
    delete_eid_emails()
    emails_in_queue = frappe.get_list('Email Queue', filters={'status': 'Not Sent'})
    for row in emails_in_queue:
        try:send_now(name=row.name)
        except:pass
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
