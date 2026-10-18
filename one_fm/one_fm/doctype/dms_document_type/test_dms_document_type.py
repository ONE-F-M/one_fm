# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.tests.test_document_request_inputs import _register


class TestDMSDocumentType(FrappeTestCase):
	def _type(self, source_guideline):
		return frappe.get_doc(
			{
				"doctype": "DMS Document Type",
				"document_type_name": "_Test DMS Type",
				"source_guideline": source_guideline,
			}
		)

	def test_an_active_guideline_is_accepted(self):
		doc = self._type(_register("Guideline", suffix="DMSType")).insert()
		self.assertTrue(doc.source_guideline)

	def test_a_finished_document_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._type(_register("SOP", suffix="DMSType")).insert()

	def test_a_withdrawn_guideline_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._type(_register("Guideline", lifecycle_state="Inactive", suffix="DMSTypeDead")).insert()
