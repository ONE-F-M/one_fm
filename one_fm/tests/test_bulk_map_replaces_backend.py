# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""While a Job Applicant Lifecycle - Bulk map runs an applicant, the code it replaces steps aside.

Each hook is checked both ways: with a running map it does nothing, without one it does what
it always did. bulk_map_running and bulk_map_handled are checked against real instances when one_bpmn is
installed.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.hiring import rejection_notification
from one_fm.hiring.bulk_map import bulk_map_handled, bulk_map_running
from one_fm.overrides import job_offer as job_offer_module
from one_fm.overrides.job_offer import JobOfferOverride
from one_fm.utils import on_update_job_applicant

APPLICANT = "HR-APP-BULK-MAP-TEST"


class TestBulkMapChecks(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "BPMN Process Instance"):
			self.skipTest("one_bpmn is not installed")

	def tearDown(self):
		frappe.db.rollback()

	def _instance(self, process_id, status, applicant=APPLICANT):
		model = frappe.get_doc(
			{"doctype": "BPMN Process Model", "name": "Bulk Map Test " + process_id, "process_id": process_id}
		)
		if not frappe.db.exists("BPMN Process Model", model.name):
			model.db_insert()
		frappe.get_doc(
			{
				"doctype": "BPMN Process Instance",
				"name": frappe.generate_hash(length=10),
				"process_model": model.name,
				"context_doctype": "Job Applicant",
				"context_docname": applicant,
				"status": status,
			}
		).db_insert()

	def _applicant(self, hiring_method):
		frappe.get_doc(
			{
				"doctype": "Job Applicant",
				"name": APPLICANT,
				"applicant_name": "Bulk Map Test",
				"one_fm_hiring_method": hiring_method,
			}
		).db_insert()

	def _checks(self):
		return bulk_map_running(APPLICANT), bulk_map_handled(APPLICANT)

	def test_a_running_bulk_map_counts_for_both(self):
		self._instance("job_applicant_bulk_test", "Active")
		self.assertEqual(self._checks(), (True, True))

	def test_a_finished_bulk_map_is_handled_but_not_running(self):
		self._instance("job_applicant_bulk_test", "Completed")
		self._applicant("Bulk Recruitment")
		self.assertEqual(self._checks(), (False, True))

	def test_a_finished_bulk_map_does_not_count_for_another_hiring_method(self):
		self._instance("job_applicant_bulk_test", "Completed")
		self._applicant("A la carte Recruitment")
		self.assertEqual(self._checks(), (False, False))

	def test_a_cancelled_or_errored_map_does_not_count(self):
		self._instance("job_applicant_bulk_test", "Cancelled")
		self._instance("job_applicant_bulk_test", "Errored")
		self._applicant("Bulk Recruitment")
		self.assertEqual(self._checks(), (False, False))

	def test_another_process_on_the_applicant_does_not_count(self):
		self._instance("job_applicant_a_la_carte_test", "Active")
		self.assertEqual(self._checks(), (False, False))

	def test_no_applicant_never_counts(self):
		self.assertFalse(bulk_map_running(None))
		self.assertFalse(bulk_map_handled(None))

	def test_a_reopened_applicant_whose_map_finished_gets_the_offer_from_the_code(self):
		self._instance("job_applicant_bulk_test", "Completed")
		self._applicant("Bulk Recruitment")
		doc = frappe._dict(name=APPLICANT, status="Accepted", one_fm_applicant_status="Selected")
		with patch("one_fm.utils.issue_job_offer_for_applicant") as issue:
			on_update_job_applicant(doc, "on_update")
		issue.assert_called_once_with(APPLICANT)


class TestJobApplicantOffersStepAside(FrappeTestCase):
	def _run(self, map_runs, stage):
		doc = frappe._dict(name=APPLICANT, status="Accepted", one_fm_applicant_status=stage)
		with (
			patch("one_fm.utils.bulk_map_running", return_value=map_runs),
			patch("one_fm.utils.issue_job_offer_for_applicant") as issue,
			patch("one_fm.utils.create_draft_job_offer_for_applicant") as draft,
		):
			on_update_job_applicant(doc, "on_update")
		return issue, draft

	def test_selected_applicant_with_a_running_map_gets_no_offer_from_the_code(self):
		issue, _ = self._run(map_runs=True, stage="Selected")
		issue.assert_not_called()

	def test_shortlisted_applicant_with_a_running_map_gets_no_draft_from_the_code(self):
		_, draft = self._run(map_runs=True, stage="Shortlisted")
		draft.assert_not_called()

	def test_applicant_without_a_map_still_gets_the_offer(self):
		issue, _ = self._run(map_runs=False, stage="Selected")
		issue.assert_called_once_with(APPLICANT)


class TestJobOfferStepsAside(FrappeTestCase):
	def _offer(self, **values):
		offer = frappe.new_doc("Job Offer")
		offer.job_applicant = APPLICANT
		offer.update(values)
		return offer

	def test_offer_with_a_running_map_is_not_sent_or_emailed_by_the_code(self):
		offer = self._offer()
		with (
			patch.object(job_offer_module, "bulk_map_running", return_value=True),
			patch.object(JobOfferOverride, "submit_job_offer_to_candidate") as submit,
			patch.object(JobOfferOverride, "auto_email_job_offer") as email,
		):
			offer.on_update()
		submit.assert_not_called()
		email.assert_not_called()

	def test_offer_without_a_map_is_still_sent_and_emailed(self):
		offer = self._offer()
		with (
			patch.object(job_offer_module, "bulk_map_running", return_value=False),
			patch.object(JobOfferOverride, "submit_job_offer_to_candidate") as submit,
			patch.object(JobOfferOverride, "auto_email_job_offer") as email,
		):
			offer.on_update()
		submit.assert_called_once()
		email.assert_called_once()

	def _accept(self, map_runs, **values):
		offer = self._offer(
			workflow_state="Submit to Onboarding Officer",
			one_fm_offer_accepted_date=frappe.utils.nowdate(),
			**values,
		)
		with (
			patch.object(job_offer_module, "bulk_map_handled", return_value=map_runs),
			patch.object(JobOfferOverride, "onload"),
			patch.object(JobOfferOverride, "validate_job_offer_mandatory_fields"),
			patch.object(JobOfferOverride, "create_candidate_country_process") as create_ccp,
			patch.object(job_offer_module, "assign_to_onboarding_officer") as assign,
		):
			offer.evaluate_tracker_pipeline()
		return assign, create_ccp

	def test_accepted_offer_with_a_running_map_is_not_handed_over_by_the_code(self):
		assign, create_ccp = self._accept(
			map_runs=True,
			estimated_date_of_joining=frappe.utils.nowdate(),
			onboarding_officer="Administrator",
		)
		assign.assert_not_called()
		create_ccp.assert_not_called()

	def test_accepted_offer_without_a_map_is_still_handed_over(self):
		assign, create_ccp = self._accept(
			map_runs=False,
			estimated_date_of_joining=frappe.utils.nowdate(),
			onboarding_officer="Administrator",
		)
		assign.assert_called_once()
		create_ccp.assert_called_once()

	def test_joining_details_are_still_required_while_a_map_runs(self):
		with self.assertRaises(frappe.ValidationError):
			self._accept(map_runs=True, estimated_date_of_joining=frappe.utils.nowdate())


class TestRejectionStepsAside(FrappeTestCase):
	def _rejected(self):
		doc = MagicMock()
		doc.name = APPLICANT
		doc.get.side_effect = {"status": rejection_notification.REJECTED}.get
		doc.get_doc_before_save.return_value = None
		return doc

	def test_rejection_with_a_running_map_is_not_stamped_by_the_code(self):
		doc = self._rejected()
		with patch.object(rejection_notification, "bulk_map_running", return_value=True):
			rejection_notification.notify_on_rejection(doc)
		doc.db_set.assert_not_called()

	def test_rejection_without_a_map_is_still_stamped(self):
		doc = self._rejected()
		with patch.object(rejection_notification, "bulk_map_running", return_value=False):
			rejection_notification.notify_on_rejection(doc)
		doc.db_set.assert_called_once()

	def _hourly(self, map_runs):
		with (
			patch.object(
				rejection_notification.frappe, "get_all", return_value=[frappe._dict(name=APPLICANT)]
			),
			patch.object(rejection_notification.frappe, "get_doc"),
			patch.object(rejection_notification.frappe.db, "set_value"),
			patch.object(rejection_notification.frappe.db, "commit"),
			patch.object(rejection_notification, "bulk_map_running", return_value=map_runs),
			patch.object(rejection_notification, "send_rejection_email", return_value=True) as send,
		):
			rejection_notification.send_due_rejection_emails()
		return send

	def test_hourly_job_leaves_a_mapped_applicant_to_the_map(self):
		self._hourly(map_runs=True).assert_not_called()

	def test_hourly_job_still_mails_an_applicant_without_a_map(self):
		self._hourly(map_runs=False).assert_called_once()
