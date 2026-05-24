# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMaintenanceWorkOrder(FrappeTestCase):
	def test_doctype_is_registered(self):
		meta = frappe.get_meta("Maintenance Work Order")

		self.assertIsNotNone(meta)
		self.assertEqual(meta.name, "Maintenance Work Order")
