# Copyright (c) 2024, ONE FM and Contributors
# See license.txt

# import frappe
import frappe
from frappe.tests.utils import FrappeTestCase


class TestClient(FrappeTestCase):
	def setUp(self):
		self.customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "Test Customer",
			"customer_group": "All Customer Groups",
			"territory": "All Territories"
		}).insert()

	def tearDown(self):
		frappe.db.rollback()

	def test_valid_gst_number(self):
		client = frappe.get_doc({
			"doctype": "Client",
			"customer": self.customer.name,
			"gst_number": "29AAFCD5862R1Z5"
		}).insert()
		self.assertEqual(client.gst_number, "29AAFCD5862R1Z5")

	def test_missing_gst_number(self):
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc({
				"doctype": "Client",
				"customer": self.customer.name
			}).insert()

	def test_invalid_gst_number(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Client",
				"customer": self.customer.name,
				"gst_number": "INVALIDGST"
			}).insert()

