# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0 import seed_record_update_properties as seed_patch

DOCTYPE = "Record Update Property"


class TestRecordUpdateProperty(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.reload_doc("one_fm", "doctype", "record_update_property")

	def test_meta_matches_ba(self):
		meta = frappe.get_meta(DOCTYPE)
		self.assertEqual((meta.is_submittable, meta.autoname, meta.module), (0, "field:property_name", "One Fm"))
		self.assertEqual(
			[(f.fieldname, f.fieldtype, f.options or "") for f in meta.fields],
			[
				("property", "Section Break", ""),
				("property_name", "Data", ""),
				("linked_doctype", "Link", "DocType"),
				("employee_field", "Data", ""),
			],
		)
		name_field = meta.get_field("property_name")
		self.assertEqual((name_field.reqd, name_field.unique, name_field.in_list_view), (1, 1, 1))
		self.assertEqual({p.role for p in meta.permissions}, {"System Manager", "HR User", "Employee"})
		employee = next(p for p in meta.permissions if p.role == "Employee")
		granted = {k for k in ("read", "select", "write", "create", "delete", "submit") if employee.get(k)}
		self.assertEqual(granted, {"read", "select"})

	def test_seed_creates_every_property_once(self):
		frappe.db.delete(DOCTYPE)
		seed_patch.execute()
		seed_patch.execute()
		rows = frappe.get_all(DOCTYPE, fields=["property_name", "linked_doctype", "employee_field"], order_by="name")
		expected = sorted(seed_patch.PROPERTIES, key=lambda p: p["property_name"])
		self.assertEqual([dict(r) for r in rows], expected)

	def test_every_seeded_employee_field_exists(self):
		meta = frappe.get_meta("Employee")
		for values in seed_patch.PROPERTIES:
			with self.subTest(property=values["property_name"]):
				self.assertTrue(meta.has_field(values["employee_field"]))
