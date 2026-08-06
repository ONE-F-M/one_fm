# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import re

import frappe
from frappe.tests.utils import FrappeTestCase


class TestVisaRequest(FrappeTestCase):
	pass


class TestReapplyAfterPamRejection(FrappeTestCase):
	"""WI-001976: a fresh request from one PAM rejected for the designation or the gender."""

	def setUp(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import (
			PAM_REJECTED_STATE,
			REAPPLY_REASONS,
		)

		self.state = PAM_REJECTED_STATE
		self.reasons = REAPPLY_REASONS

		# FrappeTestCase rolls back per class, not per test, so a reapplication made by an
		# earlier test in this class is still visible here - hence "not like %-N" rather
		# than simply the newest draft, which could be one of them.
		name = frappe.db.get_value(
			"Visa Request",
			{"docstatus": 0, "reapplied_from": ["is", "not set"]},
			"name",
			order_by="creation desc",
		)
		if not name:
			self.skipTest("no draft Visa Request on this instance to reapply from")
		self.source = name
		self._reject(self.reasons[0])

	def _reject(self, reason):
		"""Put the source in the rejected state - rolled back with the test."""
		frappe.db.set_value(
			"Visa Request",
			self.source,
			{"workflow_state": self.state, "pam_rejection_remark": reason},
			update_modified=False,
		)

	def _doc(self):
		return frappe.get_doc("Visa Request", self.source)

	def test_only_the_two_reasons_allow_a_reapplication(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import can_reapply

		for reason in self.reasons:
			self._reject(reason)
			self.assertTrue(can_reapply(self._doc()), msg=reason)

		# The reasons a fresh request would be refused for all over again.
		for reason in ("Worker is in Black List", "An active file exists for this worker", None):
			self._reject(reason)
			self.assertFalse(can_reapply(self._doc()), msg=str(reason))

	def test_a_request_in_any_other_state_cannot_be_reapplied(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import can_reapply

		frappe.db.set_value(
			"Visa Request", self.source, "workflow_state", "Pending By PAM", update_modified=False
		)
		self.assertFalse(can_reapply(self._doc()))

	def test_the_new_request_takes_the_next_amendment_number(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import reapply_visa_request

		first = reapply_visa_request(self.source)["name"]

		# The original's name plus a number - the amendment series the AC asks for.
		self.assertRegex(first, rf"^{re.escape(self.source)}-\d+$")

		# A second attempt continues the series rather than colliding, and reapplying the
		# reapplication counts from the original rather than nesting suffixes: the name
		# gains one number, not two.
		frappe.db.set_value(
			"Visa Request",
			first,
			{"workflow_state": self.state, "pam_rejection_remark": self.reasons[0]},
			update_modified=False,
		)
		second = reapply_visa_request(first)["name"]

		self.assertRegex(second, rf"^{re.escape(self.source)}-\d+$")
		self.assertEqual(int(second.rsplit("-", 1)[1]), int(first.rsplit("-", 1)[1]) + 1)

	def test_the_new_request_carries_the_applicant_and_the_link_back(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import reapply_visa_request

		source = self._doc()
		new = frappe.get_doc("Visa Request", reapply_visa_request(self.source)["name"])

		self.assertEqual(new.reapplied_from, source.name)
		self.assertEqual(new.job_offer, source.job_offer)
		self.assertEqual(new.job_applicant, source.job_applicant)
		# Enough of the applicant comes with it that the draft is valid on its own.
		self.assertEqual(new.passport_number, source.passport_number)
		self.assertEqual(new.passport_copy, source.passport_copy)

	def test_the_new_request_starts_clean_of_the_failed_attempt(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import (
			OUTCOME_FIELDS,
			reapply_visa_request,
		)

		frappe.db.set_value(
			"Visa Request",
			self.source,
			{"pam_reference_number": "PAM-123", "visa_reference_number": "VISA-9"},
			update_modified=False,
		)

		new = frappe.get_doc("Visa Request", reapply_visa_request(self.source)["name"])

		self.assertEqual(new.workflow_state, "Draft")
		for fieldname in OUTCOME_FIELDS:
			self.assertFalse(new.get(fieldname), msg=fieldname)

	def test_the_rejected_request_is_left_as_the_history(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import reapply_visa_request

		reapply_visa_request(self.source)

		source = self._doc()
		self.assertEqual(source.workflow_state, self.state)
		self.assertEqual(source.docstatus, 0)

	def test_a_request_that_does_not_qualify_is_refused_by_the_server(self):
		"""The button is only the first gate; the method has to hold on its own."""
		from one_fm.visa_management.doctype.visa_request.visa_request import reapply_visa_request

		self._reject("Worker is in Black List")

		with self.assertRaises(frappe.ValidationError):
			reapply_visa_request(self.source)
