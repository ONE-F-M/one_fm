import frappe
from frappe.email.doctype.email_queue.email_queue import send_now


FLUSH_JOB_ID = "one_fm_flush_email_queue"


def _force_send_email(name=None):
	"""Flush the whole pending email queue from a background job.

	Previously this sent one named queue row per job. With one job per mail,
	a notification burst (e.g. the 12:15 Roster Day Off Checker run, which
	creates several hundred assignments in a couple of minutes) opened a fresh
	authenticated SMTP connection per mail, dozens per minute from one IP. The
	outgoing relay throttles that and drops the connections, which surfaces as
	"Invalid Outgoing Mail Server or Port: Connection unexpectedly closed" and,
	after three retries, as permanently lost mail.

	``frappe.email.queue.flush`` instead walks the pending batch sequentially
	through a single reused SMTP session (the Email Account doc is cached, so
	its ``_smtp_server_instance`` is shared for the whole batch) and aborts the
	batch once failures pass its own threshold rather than hammering on. It
	needs no permission gate: like the scheduler, it calls ``EmailQueue.send()``
	directly rather than the whitelisted ``send_now``.

	``name`` is accepted and ignored so that jobs already queued with the old
	signature still run after a deploy.
	"""
	from frappe.email.queue import flush

	flush()


def after_insert(doc, event):
	"""
	1. Inject AMP HTML into the email MIME if ``frappe.flags.amp_html`` is set.
	2. Ask for an immediate queue flush if the recipients are not more than 19
	   records, so transactional mail does not wait for the scheduler's minute
	   tick. Bulk mail (20+ recipients) is left to the scheduler, as before.
	"""
	# ── AMP Injection ─────────────────────────────────────────────────
	# Grab the AMP content set by one_bpmn's compose_and_send_task_email
	# or dispatchers.dispatch_email before the force-send fires.
	amp_html = getattr(frappe.flags, "amp_html", None)
	frappe.flags.amp_html = None  # Always clear — even if falsy (e.g. empty string)
	if amp_html:
		try:
			_inject_amp_into_message(doc, amp_html)
		except Exception:
			frappe.log_error(
				title="AMP: Failed to inject AMP part into email",
				message=frappe.get_traceback(),
			)

	# ── Immediate flush for small queues ──────────────────────────────
	found = True
	if len(doc.recipients) >= 20:
		found = False
	if found:
		# Enqueue it safely in the background rather than blocking the main transaction.
		# Deduplicated on a fixed job id: a burst of inserts asks for one flush, not
		# one job (and one SMTP connection) per mail. Whatever is pending when the
		# flush runs goes out in that same batch, so delivery stays immediate.
		frappe.enqueue(
			_force_send_email,
			queue="short",
			# A flush walks up to email_queue_batch_size (500 by default) rows in
			# one job, so give it more than the 300s the short queue assumes. A
			# timeout here would not lose mail (sent rows are marked Sent, the row
			# left in "Sending" is reset by frappe's retry_sending_emails, the rest
			# stay pending), but it would delay the tail of a large batch.
			timeout=900,
			job_id=FLUSH_JOB_ID,
			deduplicate=True,
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

	# Update both message and amp_html in a single DB call
	update_fields = {"message": msg.as_string()}
	if doc.meta.has_field("amp_html"):
		update_fields["amp_html"] = amp_html

	doc.message = update_fields["message"]
	if "amp_html" in update_fields:
		doc.amp_html = amp_html

	frappe.db.set_value("Email Queue", doc.name, update_fields, update_modified=False)


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

