# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeeRecordUpdateRequestBenefitsItem(FrappeTestCase):
	def setUp(self):
		self.meta = frappe.get_meta("Employee Record Update Request Benefits Item")

	def test_is_child_table(self):
		self.assertEqual(self.meta.istable, 1)

	def test_field_list(self):
		self.assertEqual(
			[(f.fieldname, f.fieldtype) for f in self.meta.fields],
			[("property", "Select"), ("description", "Select")],
		)

	def test_property_select_options(self):
		field = self.meta.get_field("property")
		self.assertEqual(field.options, "\nHealth Insurance\nAccommodation\nTransportation\nCar")
		self.assertEqual(field.reqd, 1)
		self.assertEqual(field.in_list_view, 1)

	def test_description_select_options(self):
		field = self.meta.get_field("description")
		self.assertEqual(field.options, "\nProvided by Company")
		self.assertEqual(field.in_list_view, 1)
		self.assertFalse(field.reqd)
