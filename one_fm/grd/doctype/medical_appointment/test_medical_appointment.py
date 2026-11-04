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

	def test_payment_date_field_meta(self):
		meta = frappe.get_meta("Medical Appointment")
		field = meta.get_field("payment_date")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Datetime")
		self.assertEqual(field.label, "Payment Date")
		self.assertFalse(field.reqd)
		self.assertFalse(field.read_only)
		self.assertFalse(field.depends_on)
		self.assertFalse(field.allow_on_submit)

	def test_payment_references_field_order(self):
		order = [f.fieldname for f in frappe.get_meta("Medical Appointment").fields]
		start = order.index("last_name_english")
		self.assertEqual(
			order[start + 1:start + 5],
			["payment_references_section", "payment_invoice", "column_break_uuov", "payment_date"],
		)
		self.assertEqual(order[start + 5], "section_break_24")
		self.assertEqual(order.count("payment_invoice"), 1)

	def test_payment_date_is_retained_on_save(self):
		payment_date = "2026-11-04 10:30:00"
		appointment = frappe.new_doc("Medical Appointment")
		# No employee is set so the employee fetch_from fields are not resolved
		appointment.payment_date = payment_date
		appointment.insert(ignore_permissions=True, ignore_mandatory=True)
		appointment.reload()
		self.assertEqual(str(appointment.payment_date)[:19], payment_date)
		frappe.delete_doc("Medical Appointment", appointment.name, force=True)
