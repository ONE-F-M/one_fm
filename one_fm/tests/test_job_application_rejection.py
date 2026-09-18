# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002598: the candidate hears when their application is rejected.

A Job Applicant reaching ``Rejected`` was a silent end - the candidate heard nothing and
somebody had to remember to write by hand.

Which field means "rejected" was checked rather than assumed, because this applicant
carries two status-like fields:

* ``one_fm_applicant_status`` is the pipeline stage, and its options are Draft / Applicant
  Filtered / Shortlisted / Interview Scheduled / Interview / Interview Completed /
  Selected / Checked By GRD - **there is no Rejected in it at all**.
* the standard ``status`` Select offers Open / Replied / **Rejected** / Hold / Accepted.

So the transition watched is ``status``. A portal application really does produce a Job
Applicant (``templates/pages/job_application.py`` calls ``frappe.new_doc('Job Applicant')``),
which is what makes this the right document to hang it on.

The one thing that would turn a courtesy into a nuisance is sending it twice, so the
before-image test below is the important one: without it every later save of an
already-rejected applicant re-sends the same email, and a recruiter tidying a record a
week later looks to the candidate like a second rejection.
"""

import inspect
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.hiring import rejection_notification
from one_fm.hiring.rejection_notification import REJECTED, notify_on_rejection

TEMPLATE = pathlib.Path(frappe.get_app_path(
	"one_fm", "templates", "emails", "job_application_rejection.html"
))


class _Applicant(dict):
	"""The few things the notifier reads off a Job Applicant, plus its before-image."""

	def __init__(self, before=None, **values):
		super().__init__(values)
		self.doctype = "Job Applicant"
		self.name = values.get("name", "HR-APP-TEST")
		self._before = before

	def get(self, key, default=None):
		return super().get(key, default)

	def get_doc_before_save(self):
		return self._before


class TestOnlyARejectionSendsAnything(FrappeTestCase):
	def setUp(self):
		self.sent = []
		self._real = rejection_notification.sendemail
		rejection_notification.sendemail = lambda **kw: self.sent.append(kw)
		self.addCleanup(setattr, rejection_notification, "sendemail", self._real)

	def _applicant(self, status=REJECTED, previous=None, **extra):
		before = _Applicant(status=previous) if previous is not None else None
		values = {"status": status, "email_id": "candidate@example.com",
				  "applicant_name": "Test Candidate", "designation": "Security Guard"}
		values.update(extra)
		return _Applicant(before=before, **values)

	def test_a_fresh_rejection_is_sent(self):
		notify_on_rejection(self._applicant(previous="Open"))

		self.assertEqual(len(self.sent), 1)
		self.assertEqual(self.sent[0]["recipients"], ["candidate@example.com"])

	def test_an_applicant_who_is_not_rejected_is_left_alone(self):
		for status in ("Open", "Replied", "Hold", "Accepted"):
			notify_on_rejection(self._applicant(status=status, previous="Open"))

		self.assertEqual(self.sent, [])

	def test_an_already_rejected_applicant_is_not_told_twice(self):
		# The one that would turn a courtesy into a nuisance: every later save of a
		# rejected applicant would re-send the same email.
		notify_on_rejection(self._applicant(previous=REJECTED))

		self.assertEqual(self.sent, [])

	def test_a_brand_new_applicant_created_as_rejected_is_still_told(self):
		# No before-image at all. Rare, but it is a rejection the candidate has not heard.
		notify_on_rejection(self._applicant(previous=None))

		self.assertEqual(len(self.sent), 1)

	def test_nothing_is_sent_without_an_email_address(self):
		# The criterion names Email ID as the address. With none there is nobody to write
		# to, and a fallback would send a rejection to whichever address was nearest.
		notify_on_rejection(self._applicant(previous="Open", email_id=""))
		notify_on_rejection(self._applicant(previous="Open", email_id=None))

		self.assertEqual(self.sent, [])

	def test_a_padded_address_is_still_an_address(self):
		notify_on_rejection(self._applicant(previous="Open", email_id="  c@example.com  "))

		self.assertEqual(self.sent[0]["recipients"], ["c@example.com"])


class TestWhichEmailFieldIsRead(FrappeTestCase):
	"""Job Applicant carries two, and reading the wrong one sends nothing.

	This was not theory: the first end-to-end run of this feature queued no mail at all
	because the fixture populated the standard ``email_id`` and validation then blanked it.
	``one_fm.utils.set_job_applicant_fields`` runs ``doc.email_id = doc.one_fm_email_id``
	on every validate, so the standard field is a mirror, not a source.
	"""

	def setUp(self):
		self.sent = []
		real = rejection_notification.sendemail
		rejection_notification.sendemail = lambda **kw: self.sent.append(kw)
		self.addCleanup(setattr, rejection_notification, "sendemail", real)

	def _send(self, **fields):
		values = {"status": REJECTED, "applicant_name": "Test Candidate",
				  "designation": "Security Guard"}
		values.update(fields)
		notify_on_rejection(_Applicant(before=_Applicant(status="Open"), **values))
		return self.sent[-1]["recipients"] if self.sent else None

	def test_the_custom_field_the_portal_writes_is_used(self):
		# create_job_applicant_from_job_portal sets one_fm_email_id, not email_id.
		self.assertEqual(self._send(one_fm_email_id="portal@example.com"), ["portal@example.com"])

	def test_the_standard_field_alone_still_works(self):
		self.assertEqual(self._send(email_id="standard@example.com"), ["standard@example.com"])

	def test_the_custom_field_wins_when_both_are_set(self):
		# They are normally identical because validation copies one to the other. When they
		# disagree the one the portal and the mandatory check call "Email ID" is the truth.
		self.assertEqual(
			self._send(one_fm_email_id="portal@example.com", email_id="stale@example.com"),
			["portal@example.com"],
		)

	def test_a_blank_custom_field_does_not_shadow_the_standard_one(self):
		self.assertEqual(
			self._send(one_fm_email_id="", email_id="standard@example.com"),
			["standard@example.com"],
		)

	def test_the_mirror_really_is_a_mirror(self):
		# Pins the reason this class exists. If this assignment ever goes away, reading
		# email_id alone becomes safe and the fallback above is merely harmless.
		source = frappe.read_file(frappe.get_app_path("one_fm", "utils.py"))
		self.assertIn("doc.email_id = doc.one_fm_email_id", source)

	def test_both_fields_exist_on_the_doctype(self):
		meta = frappe.get_meta("Job Applicant")
		self.assertTrue(meta.get_field("one_fm_email_id"))
		self.assertTrue(meta.get_field("email_id"))


class TestTheSubjectLine(FrappeTestCase):
	def setUp(self):
		self.sent = []
		real = rejection_notification.sendemail
		rejection_notification.sendemail = lambda **kw: self.sent.append(kw)
		self.addCleanup(setattr, rejection_notification, "sendemail", real)

	def _send(self, **extra):
		values = {"status": REJECTED, "email_id": "c@example.com",
				  "applicant_name": "Test Candidate", "designation": "Security Guard"}
		values.update(extra)
		notify_on_rejection(_Applicant(before=_Applicant(status="Open"), **values))
		return self.sent[-1]["subject"]

	def test_it_is_the_wording_the_notes_specify(self):
		# The Notes override the attachment's own subject line.
		self.assertEqual(
			self._send(),
			"One Facilities Management: Update regarding your application for Security Guard",
		)

	def test_the_designation_comes_from_the_applicant(self):
		self.assertIn("Cleaner", self._send(designation="Cleaner"))

	def test_a_missing_designation_does_not_leave_a_dangling_for(self):
		# "...your application for " with nothing after it reads as a mistake.
		subject = self._send(designation=None, job_title=None)
		self.assertEqual(subject, "One Facilities Management: Update regarding your application")
		self.assertFalse(subject.rstrip().endswith("for"))

	def test_the_job_opening_stands_in_when_there_is_no_designation(self):
		self.assertIn("Night Guard", self._send(designation=None, job_title="Night Guard"))


class TestTheLetterItself(FrappeTestCase):
	"""The body is the business's wording, supplied as a document on the story."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.html = TEMPLATE.read_text()

	def test_every_paragraph_of_the_attached_template_is_present(self):
		for line in (
			"Thank you for taking the time to apply and for your interest in joining our team.",
			"We received a high volume of qualified applications for this role.",
			"We truly appreciate the effort and enthusiasm you put into your application.",
			"We wish you the very best in your job search",
			"Best regards,",
			"One Facilities Management",
		):
			self.assertIn(line, self.html)

	def test_it_never_greets_a_candidate_it_cannot_name(self):
		# The attached template has no salutation; "Dear ," would read worse than none.
		self.assertIn("{% if applicant_name %}", self.html)

	def test_it_renders(self):
		out = frappe.render_template(
			"one_fm/templates/emails/job_application_rejection.html",
			context={"applicant_name": "Test Candidate"},
		)
		self.assertIn("Dear Test Candidate", out)
		self.assertIn("One Facilities Management", out)

	def test_it_renders_without_a_name_too(self):
		out = frappe.render_template(
			"one_fm/templates/emails/job_application_rejection.html",
			context={"applicant_name": ""},
		)
		self.assertNotIn("Dear", out)
		self.assertIn("Thank you for taking the time to apply", out)


class TestHowItIsWiredUp(FrappeTestCase):
	def test_it_is_registered_on_the_applicant(self):
		hooks = frappe.read_file(frappe.get_app_path("one_fm", "hooks.py"))
		self.assertIn("one_fm.hiring.rejection_notification.notify_on_rejection", hooks)

	def test_it_runs_after_the_save_not_during_validation(self):
		# Sent from validate, a rejection that then failed to save would still have told
		# the candidate.
		hooks = frappe.read_file(frappe.get_app_path("one_fm", "hooks.py"))
		applicant = hooks.split('"Job Applicant": {', 1)[1].split("\n\t}", 1)[0]
		block = applicant.split('"on_update"', 1)[1]
		self.assertIn("rejection_notification.notify_on_rejection", block)

	def test_the_existing_handlers_are_still_registered(self):
		hooks = frappe.read_file(frappe.get_app_path("one_fm", "hooks.py"))
		applicant = hooks.split('"Job Applicant": {', 1)[1].split("\n\t}", 1)[0]
		self.assertIn("one_fm.one_fm.utils.send_notification_to_grd_or_recruiter", applicant)
		self.assertIn("one_fm.utils.on_update_job_applicant", applicant)
		self.assertIn("one_fm.utils.validate_job_applicant", applicant)

	def test_a_mail_failure_does_not_undo_the_rejection(self):
		# The status is already saved by the time this runs.
		source = inspect.getsource(rejection_notification.send_rejection_email)
		self.assertIn("except Exception:", source)
		self.assertIn("frappe.log_error(", source)

	def test_the_pipeline_status_field_is_not_what_is_watched(self):
		# one_fm_applicant_status has no Rejected option, so watching it would mean the
		# email never fired at all.
		source = inspect.getsource(rejection_notification.notify_on_rejection)
		self.assertIn('doc.get("status")', source)
		self.assertNotIn("one_fm_applicant_status", source)

		field = frappe.get_meta("Job Applicant").get_field("one_fm_applicant_status")
		if field:
			self.assertNotIn("Rejected", (field.options or "").split("\n"))

	def test_the_standard_status_field_still_offers_rejected(self):
		options = (frappe.get_meta("Job Applicant").get_field("status").options or "").split("\n")
		self.assertIn(REJECTED, options)
