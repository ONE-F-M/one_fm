# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.accommodation.doctype.accommodation_leave_movement.accommodation_leave_movement import get_last_active_checkin

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
