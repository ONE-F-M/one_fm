# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeeRecordUpdateRequestPropertiesItem(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.reload_doc("one_fm", "doctype", "employee_record_update_request_properties_item")

	def setUp(self):
		self.meta = frappe.get_meta("Employee Record Update Request Properties Item")

	def test_is_child_table(self):
		self.assertEqual(self.meta.istable, 1)

	def test_field_list(self):
		self.assertEqual(
			[(f.fieldname, f.fieldtype) for f in self.meta.fields],
			[
				("property", "Select"),
				("old_value", "Data"),
				("new_value", "Dynamic Link"),
				("new_value_doctype", "Link"),
			],
		)

	def test_property_select_options(self):
		field = self.meta.get_field("property")
		self.assertEqual(
			field.options,
			"\nDepartment\nDesignation\nDay Off Category\nNumber of Days Off\nEmployment Type\nReports to",
		)
		self.assertEqual(field.reqd, 1)
		self.assertEqual(field.in_list_view, 1)
		self.assertEqual(field.columns, 1)

	def test_old_value(self):
		field = self.meta.get_field("old_value")
		self.assertEqual(field.label, "Current Details")
		self.assertEqual(field.read_only, 1)
		self.assertEqual(field.in_list_view, 1)
		self.assertEqual(field.columns, 2)

	def test_new_value_is_dynamic_link_on_new_value_doctype(self):
		field = self.meta.get_field("new_value")
		self.assertEqual(field.label, "New Details")
		self.assertEqual(field.options, "new_value_doctype")
		self.assertEqual(field.in_list_view, 1)
		self.assertEqual(field.columns, 3)

	def test_new_value_doctype_is_hidden_link_to_doctype(self):
		field = self.meta.get_field("new_value_doctype")
		self.assertEqual(field.label, "New Details DocType")
		self.assertEqual(field.options, "DocType")
		self.assertEqual(field.hidden, 1)
