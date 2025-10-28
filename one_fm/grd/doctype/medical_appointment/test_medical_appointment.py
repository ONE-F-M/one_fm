# Copyright (c) 2025, one_fm and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import add_to_date, now_datetime

class TestMedicalAppointment(unittest.TestCase):
	def test_done_with_future_date(self):
		# Create a medical appointment with a future date
		appointment = frappe.new_doc("Medical Appointment")
		appointment.employee = "_Test Employee"
		appointment.pro_user = "Administrator"
		appointment.date_and_time_confirmation = add_to_date(now_datetime(), days=1)
		appointment.workflow_state = "Pending Confirmation"

		# Check that a validation error is thrown
		self.assertRaises(frappe.ValidationError, appointment.save)
