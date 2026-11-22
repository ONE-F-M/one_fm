# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeeRecordUpdateRequestSalaryStructureComponeItem(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.reload_doc("one_fm", "doctype", "employee_record_update_request_salary_structure_compone_item")

	def setUp(self):
		self.meta = frappe.get_meta("Employee Record Update Request Salary Structure Compone Item")

	def test_is_child_table(self):
		self.assertEqual(self.meta.istable, 1)

	def test_field_list(self):
		self.assertEqual(
			[(f.fieldname, f.fieldtype) for f in self.meta.fields],
			[("salary_component", "Data"), ("amount", "Currency")],
		)

	def test_salary_component(self):
		field = self.meta.get_field("salary_component")
		self.assertFalse(field.options)
		self.assertEqual(field.read_only, 1)
		self.assertEqual(field.allow_on_submit, 1)
		self.assertEqual(field.in_list_view, 1)

	def test_amount(self):
		field = self.meta.get_field("amount")
		self.assertEqual(field.read_only, 1)
		self.assertEqual(field.allow_on_submit, 1)
		self.assertEqual(field.in_list_view, 1)
