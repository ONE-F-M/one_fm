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
			"frappe.email.doctype.email_queue.email_queue.send_now",
			name=doc.name,
			now=frappe.flags.in_test,
			enqueue_after_commit=True,
			user="Administrator"
		)

def flush_emails():
    """
    This function flush emails not sent in queue
    :return:
    """
    delete_eid_emails()
    # Use get_all to bypass permissions
    emails_in_queue = frappe.get_all('Email Queue', filters={'status': 'Not Sent'})
    for row in emails_in_queue:
        try:
            # Call method directly on doc to bypass whitelisted function's permission check
            doc = frappe.get_doc('Email Queue', row.name)
            doc.send_now()
        except:
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
