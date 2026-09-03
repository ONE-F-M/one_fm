# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002317: one live A la carte application per candidate.

A candidate could open an application for every A la carte role going, and the
recruitment team carried all of them. One at a time now - and a rejection frees them to
try for something else, which is the part the story is explicit about.

Existing applications are seeded straight into the table rather than inserted through
the ORM: Job Applicant carries a long list of unrelated mandatory fields, and none of
them has anything to do with the rule under test.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.job_applicant import A_LA_CARTE, BULK_RECRUITMENT, REJECTED

EMAIL = "wi002317.duplicate@example.com"
OTHER_EMAIL = "wi002317.other@example.com"
SEEDED = "WI-002317-SEED-"
OPENING = "WI-002317 Opening"


def _clear():
	"""FrappeTestCase rolls back per class, not per test, so a row seeded by one test is
	still there for the next one - and a seed with no email is not caught by an email
	filter. Cleared by name instead."""
	frappe.db.delete("Job Applicant", {"name": ["like", SEEDED + "%"]})


def _seed(status="Open", method=A_LA_CARTE, email=EMAIL, standard_email=None, suffix="1"):
	"""An existing Job Applicant row, written without running validation."""
	doc = frappe.new_doc("Job Applicant")
	doc.name = SEEDED + suffix
	doc.applicant_name = "WI-002317 Seeded"
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
	doc.applicant_name = "WI-002317 Applying"
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


class TestOneLiveApplication(FrappeTestCase):
	def setUp(self):
		_clear()

	def test_a_second_application_is_refused(self):
		_seed(status="Open")

		with self.assertRaises(frappe.ValidationError) as raised:
			_applying().validate_open_a_la_carte_application()

		self.assertIn("active application", str(raised.exception).lower())

	def test_the_message_names_the_application_holding_them_up(self):
		_seed(status="Hold")

		with self.assertRaises(frappe.ValidationError) as raised:
			_applying().validate_open_a_la_carte_application()

		self.assertIn(EMAIL, str(raised.exception))
		self.assertIn("Hold", str(raised.exception))

	def test_a_rejected_application_frees_the_candidate(self):
		"""The story is explicit about this one."""
		_seed(status=REJECTED)

		_applying().validate_open_a_la_carte_application()

	def test_every_other_status_still_holds_them(self):
		for status in ("Open", "Replied", "Hold", "Accepted"):
			with self.subTest(status=status):
				frappe.db.delete("Job Applicant", {"one_fm_email_id": EMAIL})
				_seed(status=status)
				with self.assertRaises(frappe.ValidationError):
					_applying().validate_open_a_la_carte_application()

	def test_only_a_rejection_frees_them_when_there_are_several(self):
		"""One live application among rejected ones still blocks."""
		_seed(status=REJECTED, suffix="1")
		_seed(status="Open", suffix="2")

		with self.assertRaises(frappe.ValidationError):
			_applying().validate_open_a_la_carte_application()

	def test_all_rejected_frees_them(self):
		_seed(status=REJECTED, suffix="1")
		_seed(status=REJECTED, suffix="2")

		_applying().validate_open_a_la_carte_application()

	def test_a_different_candidate_is_unaffected(self):
		_seed(status="Open", email=OTHER_EMAIL)

		_applying(email=EMAIL).validate_open_a_la_carte_application()

	def test_a_bulk_application_does_not_hold_them(self):
		"""Bulk hiring takes many applicants; the rule has never applied to it."""
		_seed(status="Open", method=BULK_RECRUITMENT)

		_applying().validate_open_a_la_carte_application()

	def test_a_candidate_with_no_email_is_not_matched_to_every_other_blank(self):
		"""one_fm_email_id is optional, and blank matching blank would block everybody."""
		_seed(status="Open", email=None, standard_email=None)

		_applying(email=None, standard_email=None).validate_open_a_la_carte_application()


class TestWhichApplicationsTheRuleAppliesTo(FrappeTestCase):
	"""validate_duplicate_application is the entry point; it decides which rule runs."""

	def setUp(self):
		_clear()

	def test_bulk_recruitment_is_left_alone(self):
		_seed(status="Open", method=BULK_RECRUITMENT)

		doc = _applying(method=BULK_RECRUITMENT)
		doc.validate_duplicate_application()

	def test_a_blank_hiring_method_keeps_the_old_same_position_rule(self):
		"""2,491 applicants have no hiring method; they must not lose their check.

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
			_applying(email=EMAIL, standard_email=None).validate_open_a_la_carte_application()
