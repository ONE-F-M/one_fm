# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDocumentRequest(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.reload_doc("one_fm", "doctype", "document_request", force=True)
		frappe.clear_cache(doctype="Document Request")

	def test_the_drive_link_field_is_labelled_document_link(self):
		self.assertEqual(frappe.get_meta("Document Request").get_label("document_link"), "Document Link")
