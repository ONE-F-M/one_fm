# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestArrivalandDeployment(FrappeTestCase):
	def test_arrival_date_mandatory_for_onboarding(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Test Candidate"
		doc.onboarding_officer = "Administrator"
		doc.general_services = "Administrator"
		doc.warehouse = "Administrator"
		doc.workflow_state = "Pending Onboarding"
		
		# Should throw exception because arrival_date is missing
		self.assertRaises(frappe.ValidationError, doc.validate)
		
		# Once arrival_date is set, it should pass (for local hire since no CCP)
		doc.arrival_date = frappe.utils.today()
		doc.validate() # Should not raise exception
		
	def test_overseas_flight_details_mandatory(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Overseas Candidate"
		doc.candidate_country_process = "CCP-TEST-001"
		doc.onboarding_officer = "Administrator"
		doc.transportation_manager = "Administrator"
		doc.finance = "Administrator"
		doc.general_services = "Administrator"
		doc.warehouse = "Administrator"
		doc.workflow_state = "Pending Onboarding"
		doc.arrival_date = frappe.utils.today()
		
		# Should throw exception because flight details are missing for overseas
		self.assertRaises(frappe.ValidationError, doc.validate)


class TestOnboardingOfficerEmail(FrappeTestCase):
	def test_subject_has_the_arrival_date_and_hr_mailbox_is_copied(self):
		hiring_settings = frappe.get_single("Hiring Settings")
		hiring_settings.set(
			"arrival_department_emails",
			[
				{"department": "Onboarding", "email": "test_hr_mailbox@example.com"},
			],
		)
		hiring_settings.save()
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Test Onboarding Email"
		doc.onboarding_officer = "Administrator"
		doc.arrival_date = "2026-10-15"

		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()

		email = enqueue.call_args.kwargs
		self.assertIn(frappe.utils.formatdate("2026-10-15"), email["subject"])
		self.assertEqual(email["cc"], "test_hr_mailbox@example.com")

		doc.email_onboarding_mailbox = 0
		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()
		self.assertIsNone(enqueue.call_args.kwargs["cc"])

	def test_second_onboarding_officer_gets_the_email_and_the_task(self):
		second = "test_second_onboarding@example.com"
		if not frappe.db.exists("User", second):
			frappe.get_doc(
				{"doctype": "User", "email": second, "first_name": "Second", "send_welcome_email": 0}
			).insert()
		doc = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Second Officer",
				"arrival_date": "2026-10-15",
				"onboarding_officer": "Administrator",
				"second_onboarding_officer": second,
			}
		).insert()

		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()

		self.assertIn(second, enqueue.call_args.kwargs["recipients"])
		self.assertTrue(
			frappe.db.exists("ToDo", {"reference_name": doc.name, "allocated_to": second, "status": "Open"})
		)


class TestPendingOnboardingEditors(FrappeTestCase):
	def test_onboarding_officer_and_recruiter_can_edit_pending_onboarding(self):
		from one_fm.patches.v15_0 import (
			allow_onboarding_officer_to_edit_pending_onboarding_arrivals as patch_module,
		)

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			self.skipTest("Arrival and Deployment workflow is created by earlier patches")
		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		workflow.states = [
			d
			for d in workflow.states
			if not (d.state == "Pending Onboarding" and d.allow_edit == "Onboarding Officer")
		]
		recruiter_row = next(d for d in workflow.states if d.state == "Pending Onboarding")
		recruiter_row.message = "Test Pending Onboarding message"
		workflow.save()

		patch_module.execute()
		patch_module.execute()

		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		rows = {d.allow_edit: d for d in workflow.states if d.state == "Pending Onboarding"}
		self.assertCountEqual(rows, ["Recruiter", "Onboarding Officer"])
		self.assertEqual(rows["Onboarding Officer"].message, "Test Pending Onboarding message")
		self.assertEqual(rows["Onboarding Officer"].doc_status, rows["Recruiter"].doc_status)


class TestSupportDepartmentUsers(FrappeTestCase):
	def setUp(self):
		self.ard = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Department Users",
				"arrival_date": frappe.utils.add_days(frappe.utils.today(), 3),
				"recruiter": "Administrator",
				"onboarding_officer": "Administrator",
				"warehouse": "Administrator",
				"general_services": "Administrator",
				"operations_admin": "Administrator",
			}
		).insert()
		self.ard.workflow_state = "Pending Onboarding"
		self.ard.save()

	def test_submit_to_support_departments_names_the_empty_department(self):
		self.ard.warehouse = None
		self.ard.workflow_state = "Pending Support Departments"

		with self.assertRaises(frappe.ValidationError) as context:
			self.ard.save()
		self.assertIn("Warehouse", str(context.exception))
		self.assertFalse(
			frappe.db.exists("Arrival Acknowledgement", {"arrival_and_deployment": self.ard.name})
		)

	def test_local_hire_needs_only_its_three_departments(self):
		self.ard.workflow_state = "Pending Support Departments"
		self.ard.save()

		departments = frappe.get_all(
			"Arrival Acknowledgement", filters={"arrival_and_deployment": self.ard.name}, pluck="department"
		)
		self.assertCountEqual(departments, ["Warehouse", "General Services", "Operations"])
