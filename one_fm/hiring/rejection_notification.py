# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Tell a candidate, 48 hours later, that their application was rejected.

A Job Applicant reaching ``Rejected`` was a silent end - the candidate heard nothing, and
the recruitment team had to remember to write by hand. The email now goes out once 48
hours have elapsed since the rejection, not at the moment the status changes.

Nothing else records when a rejection happened (Job Applicant does not track changes, and
``modified`` moves on every edit), so the transition into Rejected stamps
``one_fm_rejected_on`` and clears ``one_fm_rejection_email_sent``. An hourly job,
``send_due_rejection_emails``, mails every Rejected applicant whose stamp is at least 48
hours old and whose flag is still 0, then sets the flag. Applicants rejected before the
stamp existed have no stamp and are never picked up.

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
from frappe.utils import add_to_date, now_datetime

from one_fm.processor import sendemail

REJECTED = "Rejected"
REJECTION_EMAIL_DELAY_HOURS = 48


def notify_on_rejection(doc, method=None) -> None:
	"""Stamp the rejection time when, and only when, the status becomes Rejected.

	Hung off ``on_update`` rather than ``validate`` so nothing is stamped for a change that
	then fails to save. The before-image is what makes this a TRANSITION: without it every
	later save of an already-rejected applicant would restart the 48 hour wait, and a
	recruiter tidying up a record a week later would look like a second rejection.

	``db_set`` with ``update_modified=False`` rather than ``save``: a save here would run
	the document hooks again and recurse.
	"""
	if doc.get("status") != REJECTED:
		return

	previous = doc.get_doc_before_save()
	if previous and previous.get("status") == REJECTED:
		return

	doc.db_set(
		{"one_fm_rejected_on": now_datetime(), "one_fm_rejection_email_sent": 0},
		update_modified=False,
	)


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


def send_rejection_email(doc) -> bool:
	"""One candidate, one email.

	Returns True when a mail was queued, or when there is no address to write to (retrying
	would never help). Returns False only when sending failed, so the caller can leave the
	applicant unmarked and the next hourly run retries.

	Wrapped: a failure here is a log entry rather than a traceback over the scheduler run.
	"""
	try:
		recipient = candidate_email(doc)
		if not recipient:
			# The criterion is explicit that the address comes from Email ID. With none
			# there is nobody to write to, and inventing a fallback would send a
			# rejection to whichever address happened to be nearest.
			return True

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
		return True
	except Exception:
		frappe.log_error(
			title="Job Applicant rejection email",
			message=frappe.get_traceback(),
		)
		return False


def send_due_rejection_emails() -> None:
	"""Hourly job: email every applicant rejected at least 48 hours ago and not yet mailed.

	A NULL ``one_fm_rejected_on`` is skipped on purpose - those are the historic
	rejections, which must never be mailed. The status filter skips an applicant who was
	re-opened inside the 48 hours. The flag is set only when sending succeeded, so a
	failure is retried by the next run.
	"""
	cutoff = add_to_date(now_datetime(), hours=-REJECTION_EMAIL_DELAY_HOURS)

	due = frappe.get_all(
		"Job Applicant",
		filters=[
			["status", "=", REJECTED],
			["one_fm_rejection_email_sent", "=", 0],
			["one_fm_rejected_on", "is", "set"],
			["one_fm_rejected_on", "<=", cutoff],
		],
		fields=["name"],
	)

	for row in due:
		doc = frappe.get_doc("Job Applicant", row.name)
		if send_rejection_email(doc):
			frappe.db.set_value(
				"Job Applicant",
				row.name,
				"one_fm_rejection_email_sent",
				1,
				update_modified=False,
			)
		# Commit per row so a later failure cannot roll back a mail already queued and flagged.
		frappe.db.commit()  # nosemgrep
