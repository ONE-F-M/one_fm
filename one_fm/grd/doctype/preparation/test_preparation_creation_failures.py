# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A partial submit has to say so.

PRE-REN-2026-00008 submitted 80 rows and opened 69 Work Permits and 69 Medical
Insurances where 70 of each were due. Both creators had caught the failure, logged it
and carried on, so the operator saw a clean submit and the gap only surfaced days later
when the connection badges were read against each other.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation import (
	report_document_creation_failures,
)

A_FAILURE = {
	"employee": "HR-EMP-03334",
	"employee_name": "Nicholas Nungo Muriuki",
	"document": "Work Permit",
	"reason": "Nicholas Nungo Muriuki's Relieving Date has been set to 2026-11-30. "
	"Work Permit processing is not allowed.",
}


class TestDocumentCreationFailures(FrappeTestCase):
	def setUp(self):
		frappe.clear_messages()

	def tearDown(self):
		frappe.clear_messages()

	def test_nothing_is_said_when_every_document_was_created(self):
		"""The common case must stay silent, or the dialog becomes noise to click past."""
		report_document_creation_failures([])
		self.assertEqual(frappe.get_message_log(), [])

	def test_the_failed_row_is_named(self):
		"""Employee, document and reason - enough to act on without opening the Error Log."""
		report_document_creation_failures([A_FAILURE])

		log = frappe.get_message_log()
		self.assertEqual(len(log), 1)
		message = log[0]["message"]
		self.assertIn("HR-EMP-03334", message)
		self.assertIn("Nicholas Nungo Muriuki", message)
		self.assertIn("Work Permit", message)
		self.assertIn("Relieving Date", message)

	def test_the_summary_does_not_raise(self):
		"""The submit still succeeds: a partial batch is the intended behaviour.

		`frappe.throw` here would roll the whole submit back and cost the 79 rows that
		did get their documents, which is the trade the per-row `try` exists to avoid.
		"""
		report_document_creation_failures([A_FAILURE])
		self.assertFalse(frappe.get_message_log()[0].get("raise_exception"))

	def test_every_failure_gets_a_row(self):
		"""One dialog listing all of them, not one dialog each."""
		failures = [dict(A_FAILURE, document=d) for d in ("Work Permit", "Medical Insurance")]
		report_document_creation_failures(failures)

		log = frappe.get_message_log()
		self.assertEqual(len(log), 1)
		self.assertEqual(log[0]["message"].count("<tr><td>"), 2)

	def test_the_reason_is_escaped(self):
		"""Reasons are exception text, and `frappe.throw` messages carry markup."""
		report_document_creation_failures([
			dict(A_FAILURE, reason="<b>Employee</b> <script>alert(1)</script> is not Active")
		])

		message = frappe.get_message_log()[0]["message"]
		self.assertNotIn("<script>", message)
		self.assertNotIn("<b>Employee</b>", message)
		self.assertIn("is not Active", message)
