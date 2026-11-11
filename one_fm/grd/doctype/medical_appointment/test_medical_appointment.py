# Copyright (c) 2025, one_fm and Contributors
# See license.txt

import frappe
import unittest

from one_fm.patches.v15_0 import drop_medical_appointment_field_order_setter

class TestMedicalAppointment(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.reload_doc("grd", "doctype", "medical_appointment")
		drop_medical_appointment_field_order_setter.execute()

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
			order[start + 1:start + 8],
			[
				"payment_references_section",
				"payment_invoice",
				"payment_made_via",
				"column_break_uuov",
				"payment_date",
				"bank_account",
				"section_break_24",
			],
		)
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
