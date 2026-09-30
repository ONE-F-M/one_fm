# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures, _register


class TestADeleteFinishesAfterItWithdrawsItsDocument(DocumentRequestInputFixtures, FrappeTestCase):
	"""The process withdraws the document, then saves the request as Approved."""

	def _delete_request(self, reference):
		return self._request(
			request_action="Delete",
			document_type="Knowledge Base",
			reference_document=reference,
			title=None,
			requirement_text=None,
		)

	def test_the_request_saves_once_its_own_document_is_withdrawn(self):
		reference = _register("Knowledge Base", suffix="Withdraw")
		doc = self._delete_request(reference)
		doc.insert()
		frappe.db.set_value("Document Register", reference, "lifecycle_state", "Inactive")
		doc.workflow_state = "Approved"
		doc.save()
		self.assertEqual(frappe.db.get_value("Document Request", doc.name, "workflow_state"), "Approved")

	def test_filing_a_delete_for_a_withdrawn_document_is_still_refused(self):
		reference = _register("Knowledge Base", lifecycle_state="Inactive", suffix="Gone")
		with self.assertRaises(frappe.ValidationError):
			self._delete_request(reference).insert()

	def test_repointing_a_request_at_a_withdrawn_document_is_still_refused(self):
		live = _register("Knowledge Base", suffix="Live")
		gone = _register("Knowledge Base", lifecycle_state="Inactive", suffix="Gone")
		doc = self._delete_request(live)
		doc.insert()
		doc.reference_document = gone
		with self.assertRaises(frappe.ValidationError):
			doc.save()
