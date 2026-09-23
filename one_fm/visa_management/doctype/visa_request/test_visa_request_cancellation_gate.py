# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002744: a visa that was issued has to be given back before another is asked for."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
	REJECTED_STATE,
	has_workflow_state_column,
)
from one_fm.visa_management.doctype.visa_request import visa_request as module
from one_fm.visa_management.doctype.visa_request.visa_request import (
	COMPLETED_STATE,
	IN_PROGRESS_STATES,
	cancelled_visa_requests,
)


class _Request:
	"""Just enough Visa Request to drive the rule: is it new, and who is it for?"""

	def __init__(self, job_applicant="JA-0001", name=None, is_new=True):
		self.job_applicant = job_applicant
		self.name = name
		self.job_applicant_full_name = "Dilli Bahadur Khapangi"
		self._is_new = is_new

	def is_new(self):
		return self._is_new


class _Recorder:
	def __init__(self, completed=(), released=()):
		self.completed = list(completed)
		self.released = set(released)
		self.queries = []

	def get_all(self, doctype, filters=None, pluck=None, **kwargs):
		self.queries.append((doctype, filters))
		if doctype == "Visa Request":
			return list(self.completed)
		return [name for name in self.completed if name in self.released]


class _GateTestCase(FrappeTestCase):
	def _run(self, request, completed=(), released=()):
		recorder = _Recorder(completed, released)
		original = module.frappe.get_all
		module.frappe.get_all = recorder.get_all
		try:
			module.VisaRequest.validate_previous_visa_cancelled(request)
		finally:
			module.frappe.get_all = original
		return recorder


class TestWhenItRefuses(_GateTestCase):
	def test_a_completed_request_with_no_cancellation_blocks_a_new_one(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self._run(_Request(), completed=["VR-0001"])

		self.assertIn(
			"A new Visa Request cannot be created because the existing Visa Request is "
			"completed.",
			str(caught.exception),
		)

	def test_the_message_names_the_request_still_standing(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self._run(_Request(), completed=["VR-0001"])

		self.assertIn("VR-0001", str(caught.exception))

	def test_one_uncancelled_visa_among_several_is_enough(self):
		"""Each visa the applicant holds has to be given back, not just one of them."""
		with self.assertRaises(frappe.ValidationError):
			self._run(_Request(), completed=["VR-0001", "VR-0002"], released=["VR-0001"])


class TestWhenItAllows(_GateTestCase):
	def test_a_completed_cancellation_releases_the_visa(self):
		self._run(_Request(), completed=["VR-0001"], released=["VR-0001"])

	def test_every_visa_cancelled_allows_a_new_request(self):
		self._run(
			_Request(), completed=["VR-0001", "VR-0002"], released=["VR-0001", "VR-0002"]
		)

	def test_an_applicant_with_no_completed_request_is_not_asked_about_cancellations(self):
		recorder = self._run(_Request(), completed=[])
		self.assertEqual(
			[doctype for doctype, _filters in recorder.queries], ["Visa Request"]
		)

	def test_an_existing_request_is_never_re_checked(self):
		"""It must not start refusing to save because of a state it reached itself."""
		recorder = self._run(_Request(is_new=True, name="VR-0009"), completed=[])
		self.assertTrue(recorder.queries)

		recorder = self._run(_Request(is_new=False), completed=["VR-0001"])
		self.assertEqual(recorder.queries, [])

	def test_a_request_for_nobody_is_not_checked(self):
		recorder = self._run(_Request(job_applicant=None), completed=["VR-0001"])
		self.assertEqual(recorder.queries, [])


class TestTheQueryItAsks(_GateTestCase):
	def test_it_excludes_itself_by_name(self):
		"""`name != NULL` matches nothing in SQL and would switch the rule off."""
		recorder = self._run(_Request(name=None), completed=[])
		filters = dict((f[0], f) for f in recorder.queries[0][1])
		self.assertEqual(filters["name"], ["name", "!=", ""])

	def test_it_looks_only_at_completed_requests(self):
		recorder = self._run(_Request(), completed=[])
		filters = dict((f[0], f) for f in recorder.queries[0][1])
		self.assertEqual(filters["workflow_state"], ["workflow_state", "=", COMPLETED_STATE])

	def test_completed_is_not_one_of_the_in_progress_states(self):
		"""The two rules must not both fire on the same request and contradict each other."""
		self.assertNotIn(COMPLETED_STATE, IN_PROGRESS_STATES)


class TestTheCancellationSideGuards(FrappeTestCase):
	def test_a_site_with_no_cancellation_workflow_releases_nothing(self):
		"""workflow_state on Visa Cancellation Request is a Custom Field the process map
		brings; filtering on a missing column fails the whole query rather than narrowing
		it, so it is asked for first."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "visa_management", "doctype", "visa_request", "visa_request.py"
			)
		)
		block = source.split("def cancelled_visa_requests", 1)[1]
		self.assertIn("has_workflow_state_column()", block)
		self.assertIn("return set()", block)

	def test_it_runs_against_this_site(self):
		"""Whatever this site's state, the helper answers rather than raising."""
		self.assertIsInstance(cancelled_visa_requests(["VR-0001"]), set)

	def test_a_cancelled_cancellation_does_not_release_the_visa(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "visa_management", "doctype", "visa_request", "visa_request.py"
			)
		)
		block = source.split("def cancelled_visa_requests", 1)[1]
		self.assertIn('["docstatus", "!=", 2]', block)

	def test_the_state_it_names_is_not_the_refused_one(self):
		"""WI-002608 renamed the refusal state; a cancellation the PRO refused must not
		read as one that released the visa."""
		self.assertNotEqual(COMPLETED_STATE, REJECTED_STATE)

	def test_the_column_guard_exists_on_this_site(self):
		self.assertIsInstance(has_workflow_state_column(), bool)
