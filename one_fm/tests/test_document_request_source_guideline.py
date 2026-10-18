# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The Source Guideline on a Document Request comes from its Document Type and cannot be picked."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.create_dms_document_types import execute as create_dms_document_types
from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures, _register


class TestSourceGuidelineFollowsTheDocumentType(DocumentRequestInputFixtures, FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.sop_guideline = _register("Guideline", suffix="ForSOP")
		self.manual_guideline = _register("Guideline", suffix="ForManual")
		for document_type, guideline in (("SOP", self.sop_guideline), ("Manual", self.manual_guideline)):
			self.addCleanup(
				frappe.db.set_value,
				"DMS Document Type",
				document_type,
				"source_guideline",
				frappe.db.get_value("DMS Document Type", document_type, "source_guideline"),
			)
			frappe.db.set_value("DMS Document Type", document_type, "source_guideline", guideline)

	def test_the_field_is_read_only_and_fetched_from_the_type(self):
		field = frappe.get_meta("Document Request").get_field("source_guideline")
		self.assertTrue(field.read_only)
		self.assertEqual(field.fetch_from, "document_type.source_guideline")

	def test_a_create_takes_its_types_guideline_whatever_was_sent(self):
		doc = self._request(document_type="SOP", source_guideline=self.manual_guideline)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.source_guideline, self.sop_guideline)

	def test_changing_the_type_changes_the_guideline(self):
		doc = self._request(document_type="SOP")
		doc.insert(ignore_permissions=True)
		doc.document_type = "Manual"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.source_guideline, self.manual_guideline)

	def test_an_update_carries_no_guideline(self):
		reference = _register("SOP", suffix="Revised")
		doc = self._request(request_action="Update", reference_document=reference)
		doc.insert(ignore_permissions=True)
		self.assertIsNone(doc.source_guideline)


class TestThePatchFixesOpenRequests(DocumentRequestInputFixtures, FrappeTestCase):
	def test_open_creates_get_the_types_guideline_and_approved_ones_keep_theirs(self):
		guideline = _register("Guideline", suffix="Patch")
		self.addCleanup(
			frappe.db.set_value,
			"DMS Document Type",
			"SOP",
			"source_guideline",
			frappe.db.get_value("DMS Document Type", "SOP", "source_guideline"),
		)
		frappe.db.set_value("DMS Document Type", "SOP", "source_guideline", guideline)
		open_request = self._request().insert(ignore_permissions=True)
		approved = self._request().insert(ignore_permissions=True)
		frappe.db.set_value("Document Request", open_request.name, "source_guideline", None)
		frappe.db.set_value(
			"Document Request", approved.name, {"source_guideline": None, "workflow_state": "Approved"}
		)

		create_dms_document_types()

		self.assertEqual(
			frappe.db.get_value("Document Request", open_request.name, "source_guideline"), guideline
		)
		self.assertIsNone(frappe.db.get_value("Document Request", approved.name, "source_guideline"))
