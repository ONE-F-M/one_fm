# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002490: one active A la carte application per candidate.

A candidate could open an application for every A la carte role going, and the
recruitment team carried all of them. One at a time now - and a rejection frees them to
try for something else, which is the part the story is explicit about.

Existing applications are seeded straight into the table rather than inserted through
the ORM: Job Applicant carries a long list of unrelated mandatory fields, and none of
them has anything to do with the rule under test.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.job_applicant import (
	A_LA_CARTE,
	BULK_RECRUITMENT,
	DUPLICATE_APPLICATION_MESSAGE,
	FROM_JOB_PORTAL,
	REJECTED,
	is_candidate_facing,
	is_staff,
)

EMAIL = "wi002490.duplicate@example.com"
OTHER_EMAIL = "wi002490.other@example.com"
SEEDED = "WI-002490-SEED-"
OPENING = "WI-002490 Opening"


def _clear():
	"""FrappeTestCase rolls back per class, not per test, so a row seeded by one test is
	still there for the next one - and a seed with no email is not caught by an email
	filter. Cleared by name instead."""
	frappe.db.delete("Job Applicant", {"name": ["like", SEEDED + "%"]})


def _seed(status="Open", method=A_LA_CARTE, email=EMAIL, standard_email=None, suffix="1"):
	"""An existing Job Applicant row, written without running validation."""
	doc = frappe.new_doc("Job Applicant")
	doc.name = SEEDED + suffix
	doc.applicant_name = "WI-002490 Seeded"
	doc.one_fm_email_id = email
	doc.email_id = standard_email if standard_email is not None else email
	doc.one_fm_hiring_method = method
	doc.status = status
	doc.db_insert()
	return doc.name


def _applying(email=EMAIL, method=A_LA_CARTE, standard_email=None):
	"""The application a candidate is trying to make, as validate sees it.

	Named, because insert() assigns the name before it runs validate - and both duplicate
	rules exclude `name != self.name`, which matches nothing at all while the name is
	still None.
	"""
	doc = frappe.new_doc("Job Applicant")
	doc.name = SEEDED + "APPLYING"
	doc.applicant_name = "WI-002490 Applying"
	doc.one_fm_email_id = email
	doc.email_id = standard_email if standard_email is not None else email
	doc.one_fm_hiring_method = method
	doc.status = "Open"
	return doc


class TestTheValuesTheRuleTurnsOn(FrappeTestCase):
	"""A typo in any of these makes the whole rule a silent no-op."""

	def test_the_field_offers_both_hiring_methods(self):
		options = frappe.get_meta("Job Applicant").get_field("one_fm_hiring_method").options.split("\n")

		self.assertIn(A_LA_CARTE, options)
		self.assertIn(BULK_RECRUITMENT, options)

	def test_rejected_is_a_status_the_field_offers(self):
		options = frappe.get_meta("Job Applicant").get_field("status").options.split("\n")

		self.assertIn(REJECTED, options)


class TestWhichPageTheRequestCameFrom(FrappeTestCase):
	"""The half that decides which message, and the half the first attempt got wrong.

	Keying on the session user alone said "staff" for a recruiter who opened the public
	job portal with a Desk session live in the same browser - which is how this was
	found."""

	def tearDown(self):
		frappe.flags.in_web_form = False

	def test_a_document_the_portal_flagged_is_candidate_facing(self):
		doc = _applying()
		doc.flags[FROM_JOB_PORTAL] = True

		self.assertTrue(is_candidate_facing(doc))

	def test_a_web_form_submission_is_candidate_facing(self):
		"""Frappe sets this for job-application-from and job-applications."""
		frappe.flags.in_web_form = True

		self.assertTrue(is_candidate_facing(_applying()))

	def test_a_desk_save_is_not(self):
		self.assertFalse(is_candidate_facing(_applying()))

	def test_it_does_not_need_a_document(self):
		self.assertFalse(is_candidate_facing())


class TestWhoIsStaff(FrappeTestCase):
	"""The other half: only a System User can open the Desk."""

	def test_guest_is_not_staff(self):
		self.assertFalse(is_staff("Guest"))

	def test_a_website_user_is_not_staff(self):
		"""The job-applications web form requires a login, so a candidate can be a real
		User - just not a System User."""
		website_user = frappe.db.get_value("User", {"user_type": "Website User", "enabled": 1}, "name")
		if not website_user:
			self.skipTest("no enabled Website User on this site")

		self.assertFalse(is_staff(website_user))

	def test_a_desk_user_is_staff(self):
		self.assertTrue(is_staff("Administrator"))

	def test_it_reads_the_session_user_by_default(self):
		self.assertEqual(is_staff(), is_staff(frappe.session.user))


class TestTheMessageIsTheOneTheTeamSupplied(FrappeTestCase):
	"""The candidate reads this on the job portal, so it is quoted rather than
	paraphrased - and it is only shown to the candidate."""

	def setUp(self):
		_clear()

	def _from_the_portal(self):
		doc = _applying()
		doc.flags[FROM_JOB_PORTAL] = True
		return doc

	def test_a_candidate_is_shown_it_word_for_word(self):
		_seed(status="Open")

		with self.assertRaises(frappe.ValidationError) as raised:
			self._from_the_portal().validate_active_a_la_carte_application()

		self.assertIn(DUPLICATE_APPLICATION_MESSAGE, str(raised.exception))

	def test_the_portal_shows_it_even_to_somebody_signed_in_as_staff(self):
		"""The bug this replaces: a recruiter opening the public page with a Desk session
		live in the same browser was shown the internal message on it."""
		_seed(status="Open")
		self.assertTrue(is_staff(frappe.session.user))

		with self.assertRaises(frappe.ValidationError) as raised:
			self._from_the_portal().validate_active_a_la_carte_application()

		self.assertIn(DUPLICATE_APPLICATION_MESSAGE, str(raised.exception))
		self.assertNotIn(SEEDED, str(raised.exception))

	def test_a_recruiter_is_not(self):
		"""A recruiter in the Desk was being told "Thank you for your interest in joining
		our team" about somebody else's application."""
		_seed(status="Open")

		with self.assertRaises(frappe.ValidationError) as raised:
			_applying().validate_active_a_la_carte_application()

		self.assertNotIn("Thank you for your interest", str(raised.exception))

	def test_a_recruiter_is_told_which_record_blocked_them(self):
		"""The half a candidate must not see is exactly the half staff need."""
		_seed(status="Hold")

		with self.assertRaises(frappe.ValidationError) as raised:
			_applying().validate_active_a_la_carte_application()

		self.assertIn(SEEDED + "1", str(raised.exception))
		self.assertIn("Hold", str(raised.exception))

	def test_it_carries_every_paragraph_the_team_wrote(self):
		for sentence in (
			"Thank you for your interest in joining our team.",
			"our Recruitment Team will review your profile",
			"you can have one active application at a time",
			"We appreciate your interest and look forward to being in touch.",
		):
			with self.subTest(sentence=sentence):
				self.assertIn(sentence, DUPLICATE_APPLICATION_MESSAGE)

	def test_it_does_not_name_the_record_that_blocked_them(self):
		"""A candidate sees this on the public job portal; another applicant's name, role
		and record id must not leak into it."""
		_seed(status="Hold")

		with self.assertRaises(frappe.ValidationError) as raised:
			self._from_the_portal().validate_active_a_la_carte_application()

		self.assertNotIn(SEEDED, str(raised.exception))
		self.assertNotIn("WI-002490 Seeded", str(raised.exception))


class TestOneActiveApplication(FrappeTestCase):
	def setUp(self):
		_clear()

	def test_a_second_application_is_refused(self):
		_seed(status="Open")

		with self.assertRaises(frappe.ValidationError):
			_applying().validate_active_a_la_carte_application()

	def test_a_rejected_application_frees_the_candidate(self):
		"""The story is explicit about this one."""
		_seed(status=REJECTED)

		_applying().validate_active_a_la_carte_application()

	def test_every_other_status_still_holds_them(self):
		for status in ("Open", "Replied", "Hold", "Accepted"):
			with self.subTest(status=status):
				_clear()
				_seed(status=status)
				with self.assertRaises(frappe.ValidationError):
					_applying().validate_active_a_la_carte_application()

	def test_only_a_rejection_frees_them_when_there_are_several(self):
		"""One active application among rejected ones still blocks."""
		_seed(status=REJECTED, suffix="1")
		_seed(status="Open", suffix="2")

		with self.assertRaises(frappe.ValidationError):
			_applying().validate_active_a_la_carte_application()

	def test_all_rejected_frees_them(self):
		_seed(status=REJECTED, suffix="1")
		_seed(status=REJECTED, suffix="2")

		_applying().validate_active_a_la_carte_application()

	def test_a_different_candidate_is_unaffected(self):
		_seed(status="Open", email=OTHER_EMAIL)

		_applying(email=EMAIL).validate_active_a_la_carte_application()

	def test_a_bulk_application_does_not_hold_them(self):
		"""Bulk hiring takes many applicants; the rule has never applied to it."""
		_seed(status="Open", method=BULK_RECRUITMENT)

		_applying().validate_active_a_la_carte_application()

	def test_a_candidate_with_no_email_is_not_matched_to_every_other_blank(self):
		"""one_fm_email_id is optional, and blank matching blank would block everybody."""
		_seed(status="Open", email=None, standard_email=None)

		_applying(email=None, standard_email=None).validate_active_a_la_carte_application()


class TestWhichApplicationsTheRuleAppliesTo(FrappeTestCase):
	"""validate_duplicate_application is the entry point; it decides which rule runs."""

	def setUp(self):
		_clear()

	def test_bulk_recruitment_is_left_alone(self):
		_seed(status="Open", method=BULK_RECRUITMENT)

		doc = _applying(method=BULK_RECRUITMENT)
		doc.validate_duplicate_application()

	def test_a_blank_hiring_method_keeps_the_old_same_position_rule(self):
		"""Applicants with no hiring method must not lose their existing check.

		The old rule is per position, so both records name the same opening. NULL never
		equals NULL in SQL, which is why the position has to be set for it to match at all.
		"""
		_seed(status="Open", method=None)
		frappe.db.set_value("Job Applicant", SEEDED + "1", "job_title", OPENING, update_modified=False)

		doc = _applying(method=None)
		doc.job_title = OPENING
		with self.assertRaises(frappe.ValidationError):
			doc.validate_duplicate_application()

	def test_a_blank_hiring_method_is_not_blocked_by_a_different_position(self):
		"""That rule has always been per position, and this change leaves it that way."""
		_seed(status="Open", method=None)
		frappe.db.set_value("Job Applicant", SEEDED + "1", "job_title", OPENING, update_modified=False)

		doc = _applying(method=None)
		doc.job_title = OPENING + " (other)"
		doc.validate_duplicate_application()

	def test_an_existing_record_is_never_re_checked(self):
		"""The rule is for new applications - it must not lock an open record."""
		_seed(status="Open")

		doc = _applying()
		doc.name = SEEDED + "1"
		# is_new() reads the "__islocal" key; assigning the attribute inside a class body
		# would be name-mangled and leave the doc still looking new.
		doc.set("__islocal", False)
		self.assertFalse(doc.is_new())

		doc.validate_duplicate_application()


class TestTheEmailIsFoundEitherWay(FrappeTestCase):
	"""one_fm_email_id is copied onto email_id by a validate hook that runs after this
	check, so on a new record only one of the two may be filled."""

	def setUp(self):
		_clear()

	def test_it_reads_the_custom_field_first(self):
		doc = _applying(email=EMAIL, standard_email=OTHER_EMAIL)

		self.assertEqual(doc.applicant_email(), EMAIL)

	def test_it_falls_back_to_the_standard_field(self):
		doc = _applying(email=None, standard_email=EMAIL)

		self.assertEqual(doc.applicant_email(), EMAIL)

	def test_an_existing_record_is_matched_on_either_field(self):
		"""Seeded with only the standard field filled, applying with only the custom one."""
		_seed(status="Open", email=None, standard_email=EMAIL)

		with self.assertRaises(frappe.ValidationError):
			_applying(email=EMAIL, standard_email=None).validate_active_a_la_carte_application()


class TestTheMessageSurvivesTheJobPortal(FrappeTestCase):
	"""The route the story is actually about.

	/job_application posts to create_job_applicant_from_job_portal, which wrapped the
	whole save in a bare `except` and replaced whatever came out of it with "An Error
	Occured while submitting the job application" - plus an Error Log traceback. The
	wording the team supplied could never reach the applicant it was written for.
	"""

	def _endpoint(self):
		from one_fm.templates.pages import job_application

		return job_application.create_job_applicant_from_job_portal

	def test_a_validation_message_is_not_swallowed(self):
		"""Driven through the endpoint with an argument list it cannot satisfy, so the
		save raises a ValidationError of its own: what is under test is that a
		ValidationError comes back out rather than the generic sentence."""
		from one_fm.templates.pages import job_application

		original = job_application.frappe.new_doc

		def _refuse(doctype, *args, **kwargs):
			if doctype == "Job Applicant":
				frappe.throw("WI-002490 refusal that must reach the applicant")
			return original(doctype, *args, **kwargs)

		job_application.frappe.new_doc = _refuse
		try:
			with self.assertRaises(frappe.ValidationError) as raised:
				self._endpoint()(
					applicant_name="WI-002490 Portal",
					nationality=None,
					applicant_email=EMAIL,
					applicant_mobile="0000",
					job_opening=None,
					name_of_file=None,
				)
		finally:
			job_application.frappe.new_doc = original

		self.assertIn("must reach the applicant", str(raised.exception))
		self.assertNotIn("An Error Occured", str(raised.exception))

	def test_anything_that_is_not_a_validation_error_still_reads_as_a_failure(self):
		"""The generic sentence is still right for a real fault - a missing file, a
		broken attachment - and those should still be logged."""
		from one_fm.templates.pages import job_application

		original = job_application.frappe.new_doc

		def _break(doctype, *args, **kwargs):
			# Only for the applicant: log_error builds an Error Log through the same
			# function, and breaking that too would fail the logging rather than the save.
			if doctype == "Job Applicant":
				raise RuntimeError("WI-002490 genuine fault")
			return original(doctype, *args, **kwargs)

		job_application.frappe.new_doc = _break
		try:
			with self.assertRaises(frappe.ValidationError) as raised:
				self._endpoint()(
					applicant_name="WI-002490 Portal",
					nationality=None,
					applicant_email=EMAIL,
					applicant_mobile="0000",
					job_opening=None,
					name_of_file=None,
				)
		finally:
			job_application.frappe.new_doc = original

		self.assertIn("An Error Occured", str(raised.exception))
		self.assertNotIn("genuine fault", str(raised.exception))
