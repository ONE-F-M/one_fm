# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMaintenanceHolidayList(FrappeTestCase):
	def test_doctype_is_registered(self):
		meta = frappe.get_meta("Maintenance Holiday List")

		self.assertIsNotNone(meta)
		self.assertEqual(meta.name, "Maintenance Holiday List")

	def test_new_document_can_be_created(self):
		doc = frappe.new_doc("Maintenance Holiday List")

		self.assertIsNotNone(doc)
		self.assertEqual(doc.doctype, "Maintenance Holiday List")
