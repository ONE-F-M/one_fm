# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures

BLOCKED_STATES = ("Drafting", "Pending Final Approval", "Content Rejected", "Request Rejected")


class TestDocumentRequestDeleteByState(DocumentRequestInputFixtures, FrappeTestCase):
	def _in_state(self, state):
		doc = self._request()
		doc.insert()
		frappe.db.set_value("Document Request", doc.name, "workflow_state", state)
		return doc.name

	def test_draft_and_pending_approval_can_be_deleted(self):
		for state in ("Draft", "Pending Approval"):
			name = self._in_state(state)
			frappe.delete_doc("Document Request", name, ignore_permissions=True)
			self.assertFalse(frappe.db.exists("Document Request", name))

	def test_a_request_with_no_state_can_be_deleted(self):
		doc = self._request()
		doc.insert()
		frappe.delete_doc("Document Request", doc.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Document Request", doc.name))

	def test_every_later_state_is_refused_with_the_message(self):
		for state in BLOCKED_STATES:
			name = self._in_state(state)
			with self.assertRaises(frappe.ValidationError) as ctx:
				frappe.delete_doc("Document Request", name, ignore_permissions=True)
			self.assertIn("Deletion is only permitted while in 'Draft' or 'Pending Approval'", str(ctx.exception))
			self.assertTrue(frappe.db.exists("Document Request", name))
