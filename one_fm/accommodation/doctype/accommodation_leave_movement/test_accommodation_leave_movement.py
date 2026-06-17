# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.accommodation.doctype.accommodation_leave_movement.accommodation_leave_movement import (
	get_last_active_checkin,
	has_linked_checkin,
	make_checkin_from_checkout,
)

class TestAccommodationLeaveMovement(FrappeTestCase):
	def setUp(self):
		# Create a test employee if doesn't exist
		if not frappe.db.exists("Employee", "EMP-TEST-001"):
			employee = frappe.get_doc({
				"doctype": "Employee",
				"employee": "EMP-TEST-001",
				"first_name": "Test",
				"last_name": "Employee",
				"gender": "Male",
				"date_of_joining": "2020-01-01",
				"status": "Active"
			})
			employee.insert(ignore_permissions=True)
		
		# Create a test accommodation, floor, unit, space, bed
		# This assumes these DocTypes exist and have standard fields
		# For the sake of this test, we might just need the names

	def create_leave_movement(self, movement_type, employee, docstatus=0, checkin_reference=None):
		doc = frappe.get_doc({
			"doctype": "Accommodation Leave Movement",
			"type": movement_type,
			"employee": employee,
			"checkin_checkout_date_time": frappe.utils.now_datetime(),
			"full_name": "Test Employee",
			"checkin_reference": checkin_reference,
			"docstatus": docstatus,
		})
		doc.db_insert()
		return doc

	def test_has_linked_checkin_for_draft_and_submitted_records(self):
		employee = "EMP-TEST-001"
		checkout = self.create_leave_movement("OUT", employee, docstatus=1)

		self.assertFalse(has_linked_checkin(checkout.name))

		draft_checkin = self.create_leave_movement("IN", employee, checkin_reference=checkout.name)
		self.assertTrue(has_linked_checkin(checkout.name))

		frappe.db.delete("Accommodation Leave Movement", {"name": draft_checkin.name})
		submitted_checkin = self.create_leave_movement("IN", employee, docstatus=1, checkin_reference=checkout.name)
		self.assertTrue(has_linked_checkin(checkout.name))

		frappe.db.delete("Accommodation Leave Movement", {"name": submitted_checkin.name})
		frappe.db.delete("Accommodation Leave Movement", {"name": checkout.name})

	def test_make_checkin_from_checkout_prevents_duplicate_linked_checkin(self):
		employee = "EMP-TEST-001"
		checkout = self.create_leave_movement("OUT", employee, docstatus=1)
		self.create_leave_movement("IN", employee, checkin_reference=checkout.name)

		with self.assertRaises(frappe.ValidationError):
			make_checkin_from_checkout(checkout.name)

		frappe.db.delete("Accommodation Leave Movement", {"employee": employee})
		
	def test_get_last_active_checkin(self):
		employee = "EMP-TEST-001"
		
		# Create a dummy checkin record
		checkin = frappe.get_doc({
			"doctype": "Accommodation Checkin Checkout",
			"employee": employee,
			"type": "IN",
			"checked_out": 0,
			"full_name": "Test Employee",
			"checkin_checkout_date_time": frappe.utils.now(),
			"tenant_category": "Paid Service",
			"bed": "TEST-BED-001" # Assuming this exists or validation is skipped
		})
		# We use db_insert to skip complex validations of linked fields if they don't exist in test env
		checkin.db_insert()
		
		result = get_last_active_checkin(employee)
		
		self.assertIsNotNone(result)
		self.assertEqual(result.bed, "TEST-BED-001")
		
		# Cleanup
		frappe.db.delete("Accommodation Checkin Checkout", {"employee": employee})
