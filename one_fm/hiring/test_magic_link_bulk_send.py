import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.hiring.utils import (
	MAGIC_LINK_INLINE_LIMIT,
	send_magic_link_to_applicants,
	send_magic_link_to_selected_applicants,
)


class TestSendMagicLinkToSelectedApplicants(FrappeTestCase):
	"""
	The bulk magic link action used to run every selected applicant in one web request with a
	single transaction, so a timeout or one applicant without an email address discarded the
	whole batch. These tests pin the per-applicant isolation and the background hand-off.
	"""

	def applicant(self, email="applicant@example.com"):
		return frappe._dict({
			"applicant_name": "Test Applicant",
			"designation": "Guard",
			"one_fm_email_id": email,
		})

	def test_missing_email_skips_only_that_applicant(self):
		"""One applicant without an email must not stop the rest of the batch."""
		values = {
			"JA-001": self.applicant(),
			"JA-002": self.applicant(email=None),
			"JA-003": self.applicant(),
		}
		with patch("one_fm.hiring.utils.frappe.db.get_value", side_effect=lambda dt, name, fields, as_dict=False: values[name]), \
			patch("one_fm.hiring.utils.frappe.db.commit"), \
			patch("one_fm.hiring.utils.frappe.publish_progress"), \
			patch("one_fm.hiring.utils.notify_magic_link_send_result"), \
			patch("one_fm.hiring.utils.send_applicant_doc_magic_link") as send:
			result = send_magic_link_to_applicants(list(values), "Applicant Doc")

		self.assertEqual(result["sent"], ["JA-001", "JA-003"])
		self.assertEqual([name for name, _reason in result["failed"]], ["JA-002"])
		self.assertEqual(send.call_count, 2)

	def test_failure_is_isolated_and_rolled_back(self):
		"""A failing applicant is rolled back and logged, the others still commit."""
		values = {
			"JA-001": self.applicant(),
			"JA-002": self.applicant(),
		}

		def send_side_effect(name, *args, **kwargs):
			if name == "JA-001":
				raise Exception("boom")

		with patch("one_fm.hiring.utils.frappe.db.get_value", side_effect=lambda dt, name, fields, as_dict=False: values[name]), \
			patch("one_fm.hiring.utils.frappe.db.commit") as commit, \
			patch("one_fm.hiring.utils.frappe.db.rollback") as rollback, \
			patch("one_fm.hiring.utils.frappe.publish_progress"), \
			patch("one_fm.hiring.utils.frappe.log_error"), \
			patch("one_fm.hiring.utils.notify_magic_link_send_result"), \
			patch("one_fm.hiring.utils.send_career_history_magic_link", side_effect=send_side_effect):
			result = send_magic_link_to_applicants(list(values), "Career History")

		self.assertEqual(result["sent"], ["JA-002"])
		self.assertEqual([name for name, _reason in result["failed"]], ["JA-001"])
		self.assertEqual(rollback.call_count, 1)
		self.assertEqual(commit.call_count, 1)

	def test_small_selection_runs_inline(self):
		names = ["JA-%03d" % i for i in range(MAGIC_LINK_INLINE_LIMIT)]
		with patch("one_fm.hiring.utils.send_magic_link_to_applicants") as run, \
			patch("one_fm.hiring.utils.frappe.enqueue") as enqueue:
			send_magic_link_to_selected_applicants(json.dumps(names), "Applicant Doc")

		run.assert_called_once_with(names, "Applicant Doc")
		enqueue.assert_not_called()

	def test_large_selection_is_enqueued(self):
		"""Beyond the inline limit the batch must go to a worker, not the web request."""
		names = ["JA-%03d" % i for i in range(MAGIC_LINK_INLINE_LIMIT + 1)]
		with patch("one_fm.hiring.utils.send_magic_link_to_applicants") as run, \
			patch("one_fm.hiring.utils.frappe.enqueue") as enqueue, \
			patch("one_fm.hiring.utils.frappe.msgprint"):
			send_magic_link_to_selected_applicants(json.dumps(names), "Applicant Doc")

		run.assert_not_called()
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
		self.assertEqual(enqueue.call_args.kwargs["names"], names)

	def test_invalid_magic_link_type_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			send_magic_link_to_selected_applicants(json.dumps(["JA-001"]), "Something Else")

	def test_empty_selection_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			send_magic_link_to_selected_applicants(json.dumps([]), "Applicant Doc")
