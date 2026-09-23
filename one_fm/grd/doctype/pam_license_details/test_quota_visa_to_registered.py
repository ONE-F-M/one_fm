# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002772: a visa stops being issued once its holder is a registered worker."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	WATCHED_EMPLOYEE_FIELDS,
	registered_applicants,
)

SOURCE = frappe.get_app_path(
	"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
)


def _block(name):
	return frappe.read_file(SOURCE).split(f"def {name}", 1)[1].split("\ndef ", 1)[0]


class TestWhatMakesSomebodyRegistered(FrappeTestCase):
	def test_the_residency_and_the_work_permit_expiry_together(self):
		"""Either alone is somebody mid-process; both is somebody PAM has on the licence."""
		block = _block("registered_applicants")
		self.assertIn('["under_company_residency", "=", 1]', block)
		self.assertIn('["work_permit_expiry_date", "is", "set"]', block)

	def test_an_employee_with_no_expiry_date_is_not_registered_yet(self):
		"""The story is explicit: such a request stays in Visas Issued until the date is
		set."""
		block = _block("registered_applicants")
		self.assertIn("is deliberately NOT here", block)

	def test_it_is_keyed_on_the_job_applicant(self):
		"""What the Visa Request and the Employee share, and the key WI-002442's duplicate
		rule already uses."""
		self.assertIn('["job_applicant", "in", job_applicants]', _block("registered_applicants"))

	def test_nobody_asked_about_is_nobody_looked_up(self):
		self.assertEqual(registered_applicants([]), set())
		self.assertEqual(registered_applicants(None), set())
		self.assertEqual(registered_applicants([None, ""]), set())

	def test_it_runs_against_this_site(self):
		self.assertIsInstance(registered_applicants(["JA-0001"]), set)


class TestTheSameLineDividesBothFigures(FrappeTestCase):
	def test_the_registered_count_now_requires_a_work_permit_expiry(self):
		"""An employee record that exists but has no expiry date has not been registered
		with PAM - their visa is still an issued visa, counted in the row above."""
		self.assertIn(
			".where(Employee.work_permit_expiry_date.isnotnull())",
			_block("count_quota_employees"),
		)

	def test_the_issued_count_strikes_off_whoever_arrived(self):
		"""Without this the same person is in both figures, and the available quota is
		short by one for as long as they work here."""
		block = _block("visas_issued_by_quota")
		self.assertIn("arrived = registered_applicants(", block)
		self.assertIn("released |=", block)

	def test_the_issued_count_asks_the_request_for_its_applicant(self):
		self.assertIn('"job_applicant"', _block("visas_issued_by_quota"))

	def test_a_cancellation_still_releases_the_visa_too(self):
		"""Two separate reasons a completed request stops counting; neither replaces the
		other."""
		block = _block("visas_issued_by_quota")
		self.assertIn("cancelled_visa_requests(", block)
		self.assertIn("arrived", block)


class TestWhenTheFiguresMove(FrappeTestCase):
	def test_filling_in_the_work_permit_expiry_recounts(self):
		"""The day it is filled in, one figure goes down and the other goes up."""
		self.assertIn("work_permit_expiry_date", WATCHED_EMPLOYEE_FIELDS)

	def test_creating_the_employee_recounts(self):
		"""has_value_changed answers False for every field on this Employee's insert, so
		the insert is asked about first - WI-002091's trap."""
		block = _block("update_counts_from_employee")
		self.assertIn("doc.flags.in_insert", block)

	def test_the_residency_still_moves_them_too(self):
		self.assertIn("under_company_residency", WATCHED_EMPLOYEE_FIELDS)


class TestTheFieldsItReads(FrappeTestCase):
	def test_the_employee_carries_a_job_applicant_and_an_expiry(self):
		meta = frappe.get_meta("Employee")
		self.assertEqual(meta.get_field("job_applicant").options, "Job Applicant")
		self.assertEqual(meta.get_field("work_permit_expiry_date").fieldtype, "Date")

	def test_the_visa_request_carries_the_same_applicant_link(self):
		self.assertEqual(
			frappe.get_meta("Visa Request").get_field("job_applicant").options, "Job Applicant"
		)
