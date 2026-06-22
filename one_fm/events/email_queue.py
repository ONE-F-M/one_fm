import frappe
from frappe.email.doctype.email_queue.email_queue import send_now


def after_insert(doc, event):
	"""
	1. Inject AMP HTML into the email MIME if ``frappe.flags.amp_html`` is set.
	2. Force push the email if the recipients is not more than 19 records.
	"""
	# ── AMP Injection ─────────────────────────────────────────────────
	# Grab the AMP content set by one_bpmn's compose_and_send_task_email
	# or dispatchers.dispatch_email before the force-send fires.
	amp_html = getattr(frappe.flags, "amp_html", None)
	if amp_html:
		try:
			_inject_amp_into_message(doc, amp_html)
		except Exception:
			frappe.log_error(
				title="AMP: Failed to inject AMP part into email",
				message=frappe.get_traceback(),
			)
		finally:
			frappe.flags.amp_html = None

	# ── Force-send for small queues ───────────────────────────────────
	found = True
	if len(doc.recipients) >= 20:
		found = False
	if found:
		# Enqueue it safely in the background rather than blocking the main transaction
		frappe.enqueue(
			send_now,
			name=doc.name,
			now=frappe.flags.in_test,
			enqueue_after_commit=True
		)

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


# ─── AMP MIME Helpers ─────────────────────────────────────────────────────────

def _inject_amp_into_message(doc, amp_html):
	"""Parse the serialized MIME, inject text/x-amp-html, re-serialize.

	The text/x-amp-html part is inserted between text/plain and text/html
	inside the multipart/alternative container, per the AMP for Email spec.
	Also stores the AMP HTML in the ``amp_html`` custom field for audit.
	"""
	from email import policy
	from email.parser import Parser
	from email.mime.text import MIMEText

	msg = Parser(policy=policy.SMTP).parsestr(doc.message)

	# Find the multipart/alternative container
	alt = _find_alternative(msg)
	if not alt:
		return

	amp_part = MIMEText(amp_html, "x-amp-html", "utf-8", policy=policy.SMTP)

	# Current parts: [text/plain, text/html (or multipart/related)]
	# Target order:  [text/plain, text/x-amp-html, text/html]
	parts = alt.get_payload()
	if len(parts) >= 2:
		html_part = parts.pop()          # detach HTML (last part)
		alt.attach(amp_part)             # add AMP
		alt.attach(html_part)            # re-add HTML last
	else:
		alt.attach(amp_part)             # fallback: just append

	doc.message = msg.as_string()
	doc.db_update()

	# Store on the doc for audit (requires the custom field from one_bpmn)
	if doc.meta.has_field("amp_html"):
		doc.amp_html = amp_html
		frappe.db.set_value("Email Queue", doc.name, "amp_html", amp_html)


def _find_alternative(msg):
	"""Walk the MIME tree to find the multipart/alternative part."""
	if msg.get_content_type() == "multipart/alternative":
		return msg
	if msg.is_multipart():
		for part in msg.get_payload():
			found = _find_alternative(part)
			if found:
				return found
	return None

