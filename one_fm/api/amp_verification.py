"""Send a real AMP-for-Email test message through the actual production
sending pipeline — used to verify DKIM/SPF/DMARC alignment for
notifications@one-fm.com before the Google AMP sender registration
submission, and later to send the actual submission email to Google's
review address.

Two ways to run this:

1. From ``bench console``::

	from one_fm.api.amp_verification import send_amp_verification_email
	send_amp_verification_email()
	# or send_amp_verification_email(recipient="ampforemail.whitelisting@gmail.com")

2. Automatically, once, via the companion patch
   ``one_fm.patches.v15_0.send_amp_verification_test_email`` — see that
   module for why a patch is (and isn't) an appropriate trigger for this.

Sends through ``one_bpmn.email_builder.renderer`` so the message is a
genuine AMP4Email document — the same rendering path real BPMN task
notifications use — not a synthetic stand-in.
"""

from __future__ import annotations

import frappe
from frappe import _

DEFAULT_SENDER = "notifications@one-fm.com"
DEFAULT_RECIPIENT = "s.shariff@one-fm.com"


def send_amp_verification_email(
	sender: str = DEFAULT_SENDER,
	recipient: str = DEFAULT_RECIPIENT,
) -> dict:
	"""Render and send a real AMP email from *sender* to *recipient*.

	Args:
		sender: Must be an existing ``Email Account`` with
			``enable_outgoing = 1`` — this is checked explicitly so a
			misconfiguration fails with a clear message instead of a
			confusing SMTP error.
		recipient: Defaults to the address used for DKIM verification.
			Pass ``"ampforemail.whitelisting@gmail.com"`` for the actual
			Google submission — only after verification has confirmed
			``DKIM: PASS`` for *sender*'s domain.

	Returns:
		dict with ``email_queue``, ``status``, ``error``, and
		``amp_html_length`` — inspect ``status``/``error`` to confirm the
		send actually succeeded; a truthy return does not by itself mean
		delivery succeeded, only that it was accepted for queuing/sending.

	Raises:
		frappe.ValidationError: If *sender* has no matching, outgoing-enabled
			Email Account.
	"""
	account_name = frappe.db.get_value("Email Account", {"email_id": sender}, "name")
	if not account_name:
		frappe.throw(
			_("No Email Account found for {0}.").format(sender),
			frappe.ValidationError,
		)
	if not frappe.db.get_value("Email Account", account_name, "enable_outgoing"):
		frappe.throw(
			_("Email Account '{0}' ({1}) has outgoing mail disabled.").format(
				account_name, sender
			),
			frappe.ValidationError,
		)

	from one_bpmn.email_builder.renderer import render_amp, render_html_fallback

	site_url = frappe.utils.get_url()
	task_content = {
		"subject": "AMP Verification Test — notifications@one-fm.com",
		"body": (
			"<p>This is a real message sent through the production email "
			f"pipeline from <b>{sender}</b>, to verify DKIM/SPF/DMARC "
			"alignment ahead of the Google AMP-for-Email sender "
			"registration.</p>"
		),
		"open_link": f"{site_url}/app",
		"doctype": "",
		"name": "",
	}
	amp_html = render_amp(task_content)
	html_body = render_html_fallback(task_content)

	frappe.flags.amp_html = amp_html
	email_queue = frappe.sendmail(
		recipients=[recipient],
		sender=sender,
		subject=task_content["subject"],
		message=html_body,
		now=True,
	)
	frappe.db.commit()

	status = frappe.db.get_value("Email Queue", email_queue.name, "status") if email_queue else None
	error = frappe.db.get_value("Email Queue", email_queue.name, "error") if email_queue else None
	stored_amp_html = frappe.db.get_value("Email Queue", email_queue.name, "amp_html") if email_queue else None

	result = {
		"email_queue": email_queue.name if email_queue else None,
		"status": status,
		"error": error,
		"amp_html_length": len(stored_amp_html) if stored_amp_html else 0,
	}

	frappe.logger("amp_verification").info(
		f"AMP verification email {sender} -> {recipient}: {result}"
	)
	return result
