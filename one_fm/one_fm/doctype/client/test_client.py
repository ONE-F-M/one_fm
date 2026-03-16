# Copyright (c) 2024, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestClient(FrappeTestCase):
	def test_gst_number_validation(self):
		# Create a customer if it doesn't exist
		customer_name = "Test Customer for GST"
		if not frappe.db.exists("Customer", customer_name):
			frappe.get_doc({
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_group": "All Customer Groups",
				"territory": "All Territories"
			}).insert()

		# Test valid GST (15 chars)
		client = frappe.get_doc({
			"doctype": "Client",
			"customer": customer_name,
			"gst_number": "123456789012345"
		})
		client.insert()
		self.assertEqual(len(client.gst_number), 15)

		# Test invalid GST (too short)
		client2 = frappe.get_doc({
			"doctype": "Client",
			"customer": customer_name,
			"gst_number": "12345"
		})
		self.assertRaises(frappe.ValidationError, client2.insert)

		# Test invalid GST (too long)
		client3 = frappe.get_doc({
			"doctype": "Client",
			"customer": customer_name,
			"gst_number": "1234567890123456"
		})
		self.assertRaises(frappe.ValidationError, client3.insert)
