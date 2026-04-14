import frappe

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
		# Enqueue it safely in the background rather than blocking the main transaction
		# Enqueue as Administrator to bypass permission errors in background job
		frappe.enqueue(
			"one_fm.events.email_queue.send_email_as_admin",
			name=doc.name,
			now=frappe.flags.in_test,
			enqueue_after_commit=True
		)

def send_email_as_admin(name):
	with frappe.as_admin():
		frappe.get_doc("Email Queue", name).send()

def flush_emails():
    """
    This function flush emails not sent in queue
    :return:
    """
    delete_eid_emails()
    # Use get_all to bypass permissions
    emails_in_queue = frappe.get_all('Email Queue', filters={'status': 'Not Sent'}, fields=['name'])
    for row in emails_in_queue:
        try:
            # Run as admin to ensure read/write access to Email Queue
            with frappe.as_admin():
                frappe.get_doc("Email Queue", row.name).send()
        except Exception:
            frappe.log_error(title="Email Queue Flush Failure", message=frappe.get_traceback())
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
