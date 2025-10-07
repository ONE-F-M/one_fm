# -*- coding: utf-8 -*-
# Copyright (c) 2024, ONE Championship (Pte.) Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch


class TestJobOffer(FrappeTestCase):
	def setUp(self):
		self.onboarding_officer = "test_onboarding_officer@example.com"
		if not frappe.db.exists("User", self.onboarding_officer):
			frappe.get_doc({
				"doctype": "User",
				"email": self.onboarding_officer,
				"first_name": "Test Onboarding Officer",
				"roles": [{"role": "System Manager"}]
			}).insert(ignore_permissions=True)

		self.offer_template_name = "Test Offer Template"
		if not frappe.db.exists("Job Offer Template", self.offer_template_name):
			template = frappe.get_doc({
				"doctype": "Job Offer Template",
				"title": self.offer_template_name
			})
			template.append("terms", {"offer_term": "Probation Period", "value": "3 months"})
			template.append("terms", {"offer_term": "Working Hours", "value": "9 AM to 6 PM"})
			template.insert(ignore_permissions=True)

		self.designation = "Test Developer"
		if not frappe.db.exists("Designation", self.designation):
			frappe.get_doc({
				"doctype": "Designation",
				"designation_name": self.designation,
				"custom_job_offer_term_template": self.offer_template_name
			}).insert(ignore_permissions=True)

		self.salary_structure = "Test Salary Structure"
		if not frappe.db.exists("Salary Structure", self.salary_structure):
			frappe.get_doc({
				"doctype": "Salary Structure",
				"name": self.salary_structure,
				"company": "_Test Company",
				"earnings": [
					{"salary_component": "Basic", "amount": 50000},
					{"salary_component": "HRA", "amount": 25000}
				]
			}).insert(ignore_permissions=True,
			# HACK: to bypass permission error on salary component during tests
			ignore_if_duplicate=True)

		self.erf = "TEST-ERF-001"
		if not frappe.db.exists("ERF", self.erf):
			frappe.get_doc({
				"doctype": "ERF",
				"name": self.erf,
				"designation": self.designation,
				"salary_structure": self.salary_structure,
				"salary_per_person": 75000
			}).insert(ignore_permissions=True)

		self.applicant_name = f"Test Applicant {frappe.utils.random_string(5)}"
		self.applicant_email = f"test_applicant_{frappe.utils.random_string(5)}@example.com"
		self.job_applicant = frappe.get_doc({
			"doctype": "Job Applicant",
			"applicant_name": self.applicant_name,
			"email_id": self.applicant_email,
			"designation": self.designation,
			"one_fm_erf": self.erf
		}).insert(ignore_permissions=True)

		self.email_template = "Test Job Offer Email"
		if not frappe.db.exists("Email Template", self.email_template):
			frappe.get_doc({
				"doctype": "Email Template",
				"name": self.email_template,
				"response_html": "<div>Test Email</div>"
			}).insert()

		frappe.db.set_value("Hiring Settings", "Hiring Settings", "auto_email_job_offer", 1)
		frappe.db.set_value("Hiring Settings", "Hiring Settings", "job_offer_workflow_state", "Submit for Candidate Response")
		frappe.db.set_value("Hiring Settings", "Hiring Settings", "auto_email_hiring_method", "All Recruitment")
		frappe.db.set_value("Hiring Settings", "Hiring Settings", "job_offer_email_template", self.email_template)
		frappe.db.set_value("Hiring Settings", "Hiring Settings", "job_offer_print_format", "Standard")

		if not frappe.db.exists("Letter Head", "ONE FM - Job Offer"):
			frappe.get_doc({"doctype": "Letter Head", "name": "ONE FM - Job Offer"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_validate_days_off(self):
		job_offer = self._create_job_offer()
		job_offer.number_of_days_off = 0
		with self.assertRaises(frappe.ValidationError):
			job_offer.save()

		job_offer.number_of_days_off = 8
		job_offer.day_off_category = "Weekly"
		with self.assertRaises(frappe.ValidationError):
			job_offer.save()

		job_offer.number_of_days_off = 31
		job_offer.day_off_category = "Monthly"
		with self.assertRaises(frappe.ValidationError):
			job_offer.save()

	def test_validate_mandatory_fields(self):
		job_offer = self._create_job_offer(save=False)
		job_offer.workflow_state = "Submit for Candidate Response"
		job_offer.base = 0
		job_offer.one_fm_salary_structure = None
		with self.assertRaises(frappe.ValidationError) as cm:
			job_offer.save()
		self.assertIn("Mandatory fields required", str(cm.exception))
		self.assertIn("Base", str(cm.exception))
		self.assertIn("Salary Structure", str(cm.exception))

	def test_before_cancel_with_employee(self):
		job_offer = self._create_job_offer()
		employee = frappe.get_doc({
			"doctype": "Employee",
			"employee_name": self.applicant_name,
			"company": "_Test Company",
			"date_of_joining": "2024-01-01",
			"job_offer": job_offer.name
		}).insert(ignore_permissions=True)
		job_offer.reload()
		job_offer.set("__onload", {"employee": employee.name})
		with self.assertRaises(frappe.ValidationError):
			job_offer.cancel()

	def _create_job_offer(self, **kwargs):
		data = {
			"doctype": "Job Offer",
			"job_applicant": self.job_applicant.name,
			"offer_date": "2024-01-01",
			"designation": self.designation,
			"number_of_days_off": 1,
			"day_off_category": "Weekly",
			"base": 75000,
			"one_fm_salary_structure": self.salary_structure,
			"reports_to": "test@example.com",
			"project": "Test Project",
			"operations_shift": "Test Shift",
			"operations_site": "Test Site"
		}
		data.update(kwargs)
		doc = frappe.get_doc(data)
		if kwargs.get("save", True):
			doc.insert(ignore_permissions=True)
		return doc

	def test_salary_calculation_from_structure(self):
		job_offer = self._create_job_offer(one_fm_salary_structure=self.salary_structure)
		job_offer.save()

		self.assertEqual(job_offer.one_fm_job_offer_total_salary, 75000)
		self.assertEqual(len(job_offer.one_fm_salary_details), 2)
		self.assertEqual(job_offer.one_fm_salary_details[0].salary_component, "Basic")
		self.assertEqual(job_offer.one_fm_salary_details[0].amount, 50000)
		self.assertEqual(job_offer.one_fm_salary_details[1].salary_component, "HRA")
		self.assertEqual(job_offer.one_fm_salary_details[1].amount, 25000)

	def test_salary_calculation_from_details(self):
		job_offer = self._create_job_offer(one_fm_salary_structure=None)
		job_offer.one_fm_salary_details = []
		job_offer.append("one_fm_salary_details", {"salary_component": "Basic", "amount": 60000})
		job_offer.append("one_fm_salary_details", {"salary_component": "Allowance", "amount": 10000})
		job_offer.save()

		self.assertEqual(job_offer.one_fm_job_offer_total_salary, 70000)

	def test_offer_terms_population(self):
		job_offer = self._create_job_offer(designation=self.designation, save=False)
		job_offer.job_offer_term_template = None
		job_offer.save()
		self.assertEqual(job_offer.job_offer_term_template, self.offer_template_name)
		self.assertEqual(len(job_offer.offer_terms), 2)
		self.assertEqual(job_offer.offer_terms[0].offer_term, "Probation Period")
		self.assertEqual(job_offer.offer_terms[1].offer_term, "Working Hours")

	@patch("frappe.sendmail")
	def test_auto_email_job_offer(self, mock_sendmail):
		job_offer = self._create_job_offer(save=False)
		job_offer.workflow_state = "Submit for Candidate Response"
		job_offer.save()
		job_offer.reload()
		job_offer.on_update()

		mock_sendmail.assert_called_once()
		args, kwargs = mock_sendmail.call_args
		self.assertEqual(kwargs["recipients"], [self.applicant_email])
		self.assertIn("Job Offer", kwargs["subject"])
		self.assertIn(self.applicant_name, kwargs["subject"])

	def test_assign_to_onboarding_officer(self):
		job_offer = self._create_job_offer()
		job_offer.onboarding_officer = self.onboarding_officer
		job_offer.workflow_state = "Submit to Onboarding Officer"
		job_offer.estimated_date_of_joining = "2024-02-01"
		job_offer.on_update_after_submit()

		todo = frappe.get_all("ToDo", filters={"reference_name": job_offer.name, "owner": self.onboarding_officer})
		self.assertEqual(len(todo), 1)

	def test_reset_status_on_amend(self):
		original_offer = self._create_job_offer()
		original_offer.status = "Rejected"
		original_offer.save()

		amended_offer = self._create_job_offer(amended_from=original_offer.name)
		self.assertEqual(amended_offer.status, "Awaiting Response")