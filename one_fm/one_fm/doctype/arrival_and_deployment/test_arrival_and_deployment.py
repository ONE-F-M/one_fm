# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import unittest
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


TRANSPORTATION_USER = "test_ad_transport@example.com"


class TestArrivalEndsWithTransportation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from one_fm.patches.v15_0 import end_arrival_at_transportation_confirmation

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			raise unittest.SkipTest("Arrival and Deployment workflow is created by earlier patches")
		end_arrival_at_transportation_confirmation.execute()
		if not frappe.db.exists("User", TRANSPORTATION_USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": TRANSPORTATION_USER,
					"first_name": "Transport",
					"send_welcome_email": 0,
				}
			).insert()

	def test_workflow_offers_confirm_onboarding_then_arrival_by_hire_type(self):
		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		transitions = {(t.state, t.action, t.allowed): t.condition or "" for t in workflow.transitions}

		self.assertIn(("Pending Onboarding", "Confirm Onboarding", "Onboarding Officer"), transitions)
		self.assertEqual(
			transitions[("Onboarding Confirmed", "Arrived", "Transportation Manager")],
			"doc.candidate_country_process",
		)
		self.assertEqual(
			transitions[("Onboarding Confirmed", "Did Not Arrive", "Onboarding Officer")],
			"not doc.candidate_country_process",
		)
		self.assertFalse([t for t in workflow.transitions if t.action == "Submit to Support Departments"])
		self.assertFalse(frappe.db.exists("DocType", "Arrival Acknowledgement"))

	def test_confirm_onboarding_hands_the_task_to_transportation_and_arrived_closes_it(self):
		ard = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Transport Hand Over",
				"arrival_date": "2026-10-20",
				"recruiter": "Administrator",
				"onboarding_officer": "Administrator",
				"transportation_manager": TRANSPORTATION_USER,
			}
		).insert()
		for state in ("Pending Onboarding", "Onboarding Confirmed"):
			ard.workflow_state = state
			ard.save()

		self.assertEqual(_open_assignees(ard), {TRANSPORTATION_USER})
		self.assertEqual(ard.status, "Arriving")

		ard.workflow_state = "Arrived"
		ard.save()
		self.assertEqual(_open_assignees(ard), set())
		self.assertEqual(ard.status, "Joined")

	def test_overseas_arrival_needs_the_transportation_manager_role(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_country_process = "CCP-TEST"
		doc.workflow_state = "Arrived"

		with patch("frappe.get_roles", return_value=["Onboarding Officer"]):
			self.assertRaises(frappe.ValidationError, doc.validate_workflow_role)
		with patch("frappe.get_roles", return_value=["Transportation Manager"]):
			doc.validate_workflow_role()

	def test_local_arrival_is_marked_by_the_onboarding_officer(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.workflow_state = "Did Not Arrive"

		with patch("frappe.get_roles", return_value=["Transportation Manager"]):
			self.assertRaises(frappe.ValidationError, doc.validate_workflow_role)
		with patch("frappe.get_roles", return_value=["Onboarding Officer"]):
			doc.validate_workflow_role()

	def test_overseas_onboarding_needs_a_transportation_manager(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_country_process = "CCP-TEST"
		doc.arrival_date = "2026-10-20"
		doc.workflow_state = "Onboarding Confirmed"

		with self.assertRaises(frappe.ValidationError) as context:
			doc.validate()
		self.assertIn("Transportation Manager", str(context.exception))


def _open_assignees(doc):
	return set(
		frappe.get_all(
			"ToDo",
			filters={"reference_type": doc.doctype, "reference_name": doc.name, "status": "Open"},
			pluck="allocated_to",
		)
	)


class TestCandidateDetails(FrappeTestCase):
	def test_candidate_detail_fields_fetch_from_existing_fields(self):
		meta = frappe.get_meta("Arrival and Deployment")
		for fieldname in (
			"job_applicant",
			"department",
			"gender",
			"nationality",
			"date_of_birth",
		):
			link_field, source = meta.get_field(fieldname).fetch_from.split(".")
			linked_doctype = meta.get_field(link_field).options
			self.assertTrue(
				frappe.get_meta(linked_doctype).has_field(source),
				f"{fieldname} fetches {linked_doctype}.{source}, which does not exist",
			)

	def test_designation_falls_back_to_one_fm_designation(self):
		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			get_job_applicant_designation,
		)

		with patch.object(frappe.db, "get_value", return_value=(None, "Security Guard")):
			self.assertEqual(get_job_applicant_designation("HR-APP-TEST"), "Security Guard")
		with patch.object(frappe.db, "get_value", return_value=("Janitor", "Security Guard")):
			self.assertEqual(get_job_applicant_designation("HR-APP-TEST"), "Janitor")
		self.assertIsNone(get_job_applicant_designation(None))

	def test_department_comes_from_the_candidate_country_process(self):
		self.assertEqual(
			frappe.get_meta("Arrival and Deployment").get_field("department").fetch_from,
			"candidate_country_process.department",
		)

	def test_backfill_skips_an_arrival_whose_ccp_no_longer_exists(self):
		from one_fm.patches.v15_0 import set_candidate_details_on_arrivals

		ard = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Missing CCP",
				"arrival_date": "2026-10-20",
			}
		).insert()
		frappe.db.set_value(
			"Arrival and Deployment", ard.name, "candidate_country_process", "CCP-DOES-NOT-EXIST"
		)

		set_candidate_details_on_arrivals.execute()

		self.assertIsNone(frappe.db.get_value("Arrival and Deployment", ard.name, "job_applicant"))
