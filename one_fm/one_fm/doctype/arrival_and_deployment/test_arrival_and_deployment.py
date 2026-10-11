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
		hiring_settings.set("arrival_department_emails", [
			{"department": "Onboarding", "email": "test_hr_mailbox@example.com", "use": 1},
		])
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


class TestPendingOnboardingEditors(FrappeTestCase):
	def test_onboarding_officer_and_recruiter_can_edit_pending_onboarding(self):
		from one_fm.patches.v15_0 import allow_onboarding_officer_to_edit_pending_onboarding_arrivals as patch_module

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			self.skipTest("Arrival and Deployment workflow is created by earlier patches")
		patch_module.execute()
		patch_module.execute()

		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		editors = [d.allow_edit for d in workflow.states if d.state == "Pending Onboarding"]
		self.assertCountEqual(editors, ["Recruiter", "Onboarding Officer"])
