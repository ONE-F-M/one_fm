# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002442: one Visa Request in progress per applicant.

Existing requests are seeded straight into the table rather than inserted through the ORM:
Visa Request demands a passport, an eligible age and half a dozen other fields, and none of
them has anything to do with the rule under test.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.visa_management.doctype.visa_request.visa_request import IN_PROGRESS_STATES

APPLICANT = "WI-002442-APPLICANT"
OTHER_APPLICANT = "WI-002442-OTHER-APPLICANT"
SEEDED = "WI-002442-SEED-"

# What the workflow can finish in. None of these is somebody waiting on a decision, so none
# of them holds the applicant back from being put forward again.
FINISHED_STATES = (
	"Rejected By PAM",
	"Rejected By MOI",
	"Completed",
	"Rejected",
	"Rejected for Re Issue",
	"Awaiting Visa Cancellation",
	"Pending Cancel Work Permit",
	"Work Permit Cancelled",
)


def _clear():
	"""FrappeTestCase rolls back per class, not per test, so a row seeded by one test is
	still there for the next."""
	frappe.db.delete("Visa Request", {"name": ["like", SEEDED + "%"]})


def _seed(workflow_state, applicant=APPLICANT, suffix="1"):
	doc = frappe.new_doc("Visa Request")
	doc.name = SEEDED + suffix
	doc.job_applicant = applicant
	doc.workflow_state = workflow_state
	doc.db_insert()
	return doc.name


def _applying(applicant=APPLICANT):
	"""The request somebody is trying to raise, as validate sees it.

	Named, because the rule excludes `name != self.name` and that clause matches nothing at
	all while the name is still None.
	"""
	doc = frappe.new_doc("Visa Request")
	doc.name = SEEDED + "APPLYING"
	doc.job_applicant = applicant
	doc.job_applicant_full_name = "WI-002442 Applicant"
	doc.workflow_state = "Draft"
	return doc


class TestTheStatesTheRuleTurnsOn(FrappeTestCase):
	"""Every state is compared by string. One in the wrong case names nothing, and the rule
	silently stops covering that step - which is the trap the BA export keeps setting with
	"Pending by MOI"."""

	def test_every_blocking_state_is_a_real_workflow_state(self):
		workflow = frappe.db.get_value(
			"Workflow", {"document_type": "Visa Request", "is_active": 1}, "name"
		)
		if not workflow:
			self.skipTest("no active Visa Request workflow on this site")

		states = set(
			frappe.get_all(
				"Workflow Document State",
				filters={"parent": workflow, "parenttype": "Workflow"},
				pluck="state",
			)
		)

		for state in IN_PROGRESS_STATES:
			with self.subTest(state=state):
				self.assertIn(state, states)

	def test_the_two_the_story_names_as_freeing_are_not_blocking(self):
		self.assertNotIn("Rejected By PAM", IN_PROGRESS_STATES)
		self.assertNotIn("Rejected By MOI", IN_PROGRESS_STATES)

	def test_the_two_the_story_left_out_are_blocking(self):
		"""Draft and Awaiting Quota Availability are live requests somebody is carrying."""
		self.assertIn("Draft", IN_PROGRESS_STATES)
		self.assertIn("Awaiting Quota Availability", IN_PROGRESS_STATES)


class TestARequestInProgressBlocksAnother(FrappeTestCase):
	def setUp(self):
		_clear()

	def test_every_in_progress_state_blocks(self):
		for state in IN_PROGRESS_STATES:
			with self.subTest(state=state):
				_clear()
				_seed(state)
				with self.assertRaises(frappe.ValidationError):
					_applying().validate_no_request_in_progress()

	def test_a_blank_state_counts_as_a_draft(self):
		"""A row written outside the workflow carries no state, and is still a live
		request. Frappe only writes the comparison as ifnull() because None is in the
		list - drop it and these rows stop matching."""
		_seed(None)

		with self.assertRaises(frappe.ValidationError):
			_applying().validate_no_request_in_progress()

	def test_the_message_points_at_the_request_holding_them_up(self):
		_seed("Pending By PAM")

		with self.assertRaises(frappe.ValidationError) as raised:
			_applying().validate_no_request_in_progress()

		self.assertIn(SEEDED + "1", str(raised.exception))
		self.assertIn("Pending By PAM", str(raised.exception))


class TestAFinishedRequestDoesNot(FrappeTestCase):
	def setUp(self):
		_clear()

	def test_every_finished_state_frees_the_applicant(self):
		for state in FINISHED_STATES:
			with self.subTest(state=state):
				_clear()
				_seed(state)
				_applying().validate_no_request_in_progress()

	def test_one_in_progress_among_finished_ones_still_blocks(self):
		_seed("Completed", suffix="1")
		_seed("Rejected By PAM", suffix="2")
		_seed("Pending By MOI", suffix="3")

		with self.assertRaises(frappe.ValidationError):
			_applying().validate_no_request_in_progress()

	def test_several_finished_ones_do_not(self):
		"""An applicant put through the process twice before is not blocked by either."""
		_seed("Completed", suffix="1")
		_seed("Rejected By PAM", suffix="2")

		_applying().validate_no_request_in_progress()


class TestWhoTheRuleAppliesTo(FrappeTestCase):
	def setUp(self):
		_clear()

	def test_a_different_applicant_is_unaffected(self):
		_seed("Pending By PAM", applicant=OTHER_APPLICANT)

		_applying(applicant=APPLICANT).validate_no_request_in_progress()

	def test_a_request_with_no_applicant_is_left_alone(self):
		"""job_applicant is mandatory, so this cannot be saved anyway - but matching blank
		against blank would block every such draft against every other one."""
		_seed("Pending By PAM", applicant=None)

		doc = _applying(applicant=None)
		doc.validate_no_request_in_progress()

	def test_an_existing_request_is_never_re_checked(self):
		"""Re-checking on every save would make a request unsaveable the moment it entered
		one of these states - it would find itself."""
		_seed("Pending By PAM", suffix="1")

		doc = _applying()
		doc.name = SEEDED + "1"
		# is_new() reads the "__islocal" key rather than an attribute.
		doc.set("__islocal", False)
		self.assertFalse(doc.is_new())

		doc.validate_no_request_in_progress()

	def test_a_reapplication_after_a_pam_rejection_is_still_allowed(self):
		"""WI-001976 raises a fresh request from one PAM rejected. That state has to stay
		outside the blocking list or the reapply button would refuse its own output."""
		_seed("Rejected By PAM")

		_applying().validate_no_request_in_progress()
