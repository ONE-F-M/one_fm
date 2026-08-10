# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, add_years, nowdate

from one_fm.visa_management.doctype.visa_request.visa_request import (
	MINIMUM_APPLICANT_AGE_YEARS,
	MINIMUM_PASSPORT_VALIDITY_MONTHS,
)


class TestApplicantEligibility(FrappeTestCase):
	"""WI-001975: a Draft Visa Request has to clear the passport and age rules.

	Built with new_doc and validated in memory rather than inserted: the eligibility
	check runs in validate(), and a Visa Request needs a Job Offer, a Job Applicant and a
	passport copy before it would insert - none of which this rule looks at.
	"""

	def _draft(self, **overrides):
		issued = "2020-01-01"
		visa_request = frappe.new_doc("Visa Request")
		visa_request.update(
			{
				"workflow_state": "Draft",
				"passport_issued_on": issued,
				"passport_expires_on": add_years(issued, 10),
				"date_of_birth": add_years(nowdate(), -30),
				**overrides,
			}
		)
		return visa_request

	def test_a_valid_applicant_passes(self):
		self._draft().validate_applicant_eligibility()

	def test_a_passport_short_of_the_minimum_validity_is_refused(self):
		issued = "2020-01-01"
		visa_request = self._draft(
			passport_issued_on=issued,
			passport_expires_on=add_days(add_months(issued, MINIMUM_PASSPORT_VALIDITY_MONTHS), -1),
		)

		with self.assertRaises(frappe.ValidationError) as caught:
			visa_request.validate_applicant_eligibility()
		self.assertIn("passport validity must be at least 18 months", str(caught.exception))

	def test_a_passport_exactly_at_the_minimum_validity_passes(self):
		""""At least" 18 months, so the boundary is allowed."""
		issued = "2020-01-01"
		self._draft(
			passport_issued_on=issued,
			passport_expires_on=add_months(issued, MINIMUM_PASSPORT_VALIDITY_MONTHS),
		).validate_applicant_eligibility()

	def test_an_applicant_below_the_minimum_age_is_refused(self):
		visa_request = self._draft(
			date_of_birth=add_days(add_years(nowdate(), -MINIMUM_APPLICANT_AGE_YEARS), 1)
		)

		with self.assertRaises(frappe.ValidationError) as caught:
			visa_request.validate_applicant_eligibility()
		self.assertIn("at least 21 years old", str(caught.exception))

	def test_an_applicant_who_turns_of_age_today_passes(self):
		self._draft(
			date_of_birth=add_years(nowdate(), -MINIMUM_APPLICANT_AGE_YEARS)
		).validate_applicant_eligibility()

	def test_a_record_past_draft_is_left_alone(self):
		"""A passport ages while the application is in progress; that must not strand it."""
		issued = "2020-01-01"
		self._draft(
			workflow_state="Pending By PAM",
			passport_issued_on=issued,
			passport_expires_on=add_months(issued, 1),
			date_of_birth=nowdate(),
		).validate_applicant_eligibility()

	def test_missing_dates_are_not_treated_as_failures(self):
		"""Both passport dates are mandatory on the form; date of birth is not."""
		self._draft(date_of_birth=None).validate_applicant_eligibility()
		self._draft(passport_issued_on=None, passport_expires_on=None).validate_applicant_eligibility()
