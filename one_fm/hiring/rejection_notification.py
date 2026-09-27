# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-002598: tell a candidate when their application is rejected.

A Job Applicant reaching ``Rejected`` was a silent end - the candidate heard nothing, and
the recruitment team had to remember to write by hand. The email goes out the moment the
status changes, which is comfortably inside the criterion's 48 hours.

Which field means "rejected" was checked rather than assumed. A portal application creates
a Job Applicant (``templates/pages/job_application.py``), and the applicant carries two
status-like fields: ``one_fm_applicant_status`` is the pipeline stage and has no Rejected
option at all (Draft / Shortlisted / Interview / Selected), while the standard ``status``
Select is the one that offers Open / Replied / **Rejected** / Hold / Accepted. So the
transition watched here is ``status``.

The body is the template attached to the story, kept verbatim; only the subject is the
story's own, because the Notes override the attachment's.
"""

import frappe
from frappe import _

from one_fm.processor import sendemail

REJECTED = "Rejected"


def notify_on_rejection(doc, method=None) -> None:
	"""Send the rejection email when, and only when, the status becomes Rejected.

	Hung off ``on_update`` rather than ``validate`` so nothing is sent for a change that
	then fails to save. The before-image is what makes this a TRANSITION: without it every
	later save of an already-rejected applicant would send the candidate the same email
	again, and a recruiter tidying up a record a week later would look like a second
	rejection.
	"""
	if doc.get("status") != REJECTED:
		return

	previous = doc.get_doc_before_save()
	if previous and previous.get("status") == REJECTED:
		return

	send_rejection_email(doc)


def candidate_email(doc) -> str:
	"""The address the criterion means by "the Email ID field".

	There are two, and only one of them is authoritative. ``one_fm_email_id`` is what the
	portal writes (``create_job_applicant_from_job_portal``) and what the app's own
	mandatory-field check labels "Email ID"; the standard ``email_id`` is a MIRROR of it -
	``set_job_applicant_fields`` runs ``doc.email_id = doc.one_fm_email_id`` on every
	validate, which also means it blanks ``email_id`` whenever the custom one is empty.

	Reading the mirror alone is therefore not safe: an applicant whose custom field is set
	is fine, but anything that reaches this with only the standard field populated loses
	it on the next save. The custom field is preferred and the standard one is the
	fallback, so both shapes reach the candidate.
	"""
	for fieldname in ("one_fm_email_id", "email_id"):
		value = (doc.get(fieldname) or "").strip()
		if value:
			return value
	return ""


def send_rejection_email(doc) -> None:
	"""One candidate, one email.

	Wrapped: a rejection that has been recorded must stay recorded even if the mail server
	is unreachable, so a failure here is a log entry rather than a traceback over the
	recruiter's save.
	"""
	try:
		recipient = candidate_email(doc)
		if not recipient:
			# The criterion is explicit that the address comes from Email ID. With none
			# there is nobody to write to, and inventing a fallback would send a
			# rejection to whichever address happened to be nearest.
			return

		designation = doc.get("designation") or doc.get("job_title") or ""
		subject = _("One Facilities Management: Update regarding your application for {0}").format(
			designation
		) if designation else _(
			"One Facilities Management: Update regarding your application"
		)

		message = frappe.render_template(
			"one_fm/templates/emails/job_application_rejection.html",
			context={"applicant_name": doc.get("applicant_name") or ""},
		)

		sendemail(
			recipients=[recipient],
			subject=subject,
			content=message,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
			# A candidate is not a User of this system. Without this, sendemail runs the
			# address through is_email_notifications_allowed - a check about an internal
			# user's notification preferences - and silently drops every recipient who
			# has no User record, which is every candidate. Verified: the mail queued
			# nothing at all until this was set.
			is_external_mail=True,
		)
	except Exception:
		frappe.log_error(
			title="Job Applicant rejection email",
			message=frappe.get_traceback(),
		)
