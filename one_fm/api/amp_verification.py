"""Send a real AMP-for-Email test message through the actual production
sending pipeline — used to verify DKIM/SPF/DMARC alignment for
notifications@one-fm.com before the Google AMP sender registration
submission, and later to send the actual submission email to Google's
and Yahoo's review addresses.

Two ways to run this:

1. From ``bench console``::

	from one_fm.api.amp_verification import send_amp_verification_email
	send_amp_verification_email()
	# or send_amp_verification_email(recipients="ampforemail.whitelisting@gmail.com")

2. Automatically, once, via the companion patch
   ``one_fm.patches.v15_0.send_work_item_notify_assignee_demo_email`` —
   see that module for why a patch is (and isn't) an appropriate trigger
   for this.

Sends through ``one_bpmn.email_builder.renderer`` so the message is a
genuine AMP4Email document — the same rendering path real BPMN task
notifications use — not a synthetic stand-in.

The email itself is a realistic "Notify Assignee" Work Item
notification, with a genuine one-click "Start Work" action (not a
plain text link). "Start Work" is a real transition on Work Item's
Frappe Workflow (``Open`` -> ``In Progress`` — see
``frappe_agile/frappe_agile/custom/workflow/work_item.json``),
registered for AMP one-click actions via the generic
``amp_workflow_actions`` hook (``frappe_agile/hooks.py``) and processed
by ``one_bpmn.api.workflow_actions.handle_workflow_action``. Clicking
the button in the email genuinely calls ``apply_workflow`` on the real
target Work Item — this is a deliberate, confirmed side effect for the
verification document used here, not an inert demo link.
"""

from __future__ import annotations

import frappe
from frappe import _

DEFAULT_SENDER = "notifications@one-fm.com"
DEFAULT_RECIPIENTS = [
	"ampforemail.whitelisting@gmail.com",
	"ampverification@yahoo.com",
]


def send_amp_verification_email(
	sender: str = DEFAULT_SENDER,
	recipients: list[str] | str | None = None,
	work_item_id: str = "WI-001663",
	assignee_user: str = "k.sharma@one-fm.com",
) -> dict:
	"""Render and send a real AMP email from *sender* to *recipients*.

	Args:
		sender: Must be an existing ``Email Account`` with
			``enable_outgoing = 1`` — this is checked explicitly so a
			misconfiguration fails with a clear message instead of a
			confusing SMTP error.
		recipients: Defaults to both AMP verification addresses
			(Gmail's ``ampforemail.whitelisting@gmail.com`` and Yahoo's
			``ampverification@yahoo.com``) so one send satisfies both
			registrations. Pass a single address (as a string) to target
			just one.
		work_item_id: Used consistently in the subject, the Work Item
			table row, the token payload, and the "Open in ERPNext" link.
		assignee_user: The Frappe user the action token is issued for —
			must hold a role allowed by the "Start Work" transition
			(Developer or Business Analyst) for the click to succeed.

	Returns:
		dict with ``email_queue``, ``status``, ``error``, and
		``amp_html_length`` — inspect ``status``/``error`` to confirm the
		send actually succeeded; a truthy return does not by itself mean
		delivery succeeded, only that it was accepted for queuing/sending.

	Raises:
		frappe.ValidationError: If *sender* has no matching, outgoing-enabled
			Email Account.
	"""
	if recipients is None:
		recipients = DEFAULT_RECIPIENTS
	elif isinstance(recipients, str):
		recipients = [recipients]

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
	from one_bpmn.utils.token import generate_doc_action_token

	work_item_url = f"https://one-fm.com/app/work-item/{work_item_id}"
	work_item_title = "Refactor AI Model, AI Provider and AI Model pricing doctype"
	title = f"[{work_item_id}] Assigned to you: {work_item_title} (Medium priority)"

	body = f"""
<p style="margin:1em 0!important">Hi,</p>
<p style="margin:1em 0!important">A work item has been assigned to you and is ready to start.</p>
<table cellpadding="6" border="0">
<tbody>
<tr><td><b>Work Item</b></td><td>{work_item_id} &mdash; {work_item_title}</td></tr>
<tr><td><b>Type</b></td><td>User Story</td></tr>
<tr><td><b>Priority</b></td><td>Medium</td></tr>
<tr><td><b>Sprint</b></td><td>AI-013 (Active)</td></tr>
<tr><td><b>Story Points</b></td><td>0</td></tr>
<tr><td><b>Epic</b></td><td>WI-1685450</td></tr>
<tr><td><b>Reported By</b></td><td><a href="mailto:k.sharma@one-fm.com">k.sharma@one-fm.com</a></td></tr>
<tr><td><b>PR Required</b></td><td>No</td></tr>
<tr><td><b>Research Required</b></td><td>No</td></tr>
</tbody>
</table>
<p style="margin:1em 0!important"><b>Description</b><br></p>
<p style="margin:0!important">{work_item_title}</p>
""".strip()

	start_work_token = generate_doc_action_token(
		doctype="Work Item",
		docname=work_item_id,
		action="Start Work",
		user=assignee_user,
	)

	task_content = {
		"subject": title,
		"body": body,
		"actions": [
			{"label": "Start Work", "token": start_work_token, "primary": True},
		],
		"open_link": work_item_url,
		"doctype": "Work Item",
		"name": work_item_id,
		"action_endpoint": "https://one-fm.com/api/method/one_bpmn.api.workflow_actions.handle_workflow_action",
	}
	amp_html = render_amp(task_content)
	html_body = render_html_fallback(task_content)

	frappe.flags.amp_html = amp_html
	email_queue = frappe.sendmail(
		recipients=recipients,
		sender=sender,
		subject=title,
		message=html_body,
		now=True,
	)
	frappe.db.commit()

	status = frappe.db.get_value("Email Queue", email_queue.name, "status") if email_queue else None
	error = frappe.db.get_value("Email Queue", email_queue.name, "error") if email_queue else None

	stored_amp_html = None
	if email_queue and frappe.get_meta("Email Queue").has_field("amp_html"):
		stored_amp_html = frappe.db.get_value("Email Queue", email_queue.name, "amp_html")

	result = {
		"email_queue": email_queue.name if email_queue else None,
		"status": status,
		"error": error,
		"amp_html_length": len(stored_amp_html) if stored_amp_html else 0,
	}

	return result
