# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002884: the Customer's Full Name In Arabic is mandatory."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.customer import get_customer_custom_fields
from one_fm.patches.v15_0.make_customer_arabic_name_mandatory import FIELD

FIELDNAME = "customer_name_in_arabic"


def _field():
	for fields in get_customer_custom_fields().values():
		for field in fields:
			if field["fieldname"] == FIELDNAME:
				return field
	raise AssertionError(f"{FIELDNAME} is not in the Customer custom field set")


class TestTheFixture(FrappeTestCase):
	def test_the_field_is_mandatory(self):
		self.assertEqual(_field()["reqd"], 1)

	def test_nothing_else_about_it_moved(self):
		"""The story says the field is already there; only the flag is this story's."""
		field = _field()
		self.assertEqual(field["fieldtype"], "Data")
		self.assertEqual(field["label"], "Full Name In Arabic")
		self.assertEqual(field["insert_after"], "customer_name")
		self.assertEqual(field["translatable"], 1)


class TestItReachesAnExistingSite(FrappeTestCase):
	"""The half the fixture alone cannot do."""

	def setUp(self):
		self.source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "make_customer_arabic_name_mandatory.py"
			)
		)

	def test_the_fixture_is_not_applied_after_install(self):
		"""get_custom_fields() is called by after_install and by add_update_custom_field,
		which ran on 2026-01-04 and will not run again. Editing the fixture alone changes
		nothing on a site that already has the row."""
		setup = frappe.read_file(frappe.get_app_path("one_fm", "setup", "setup.py"))
		self.assertIn("def after_install():", setup)
		self.assertIn("_create_custom_fields_resiliently(get_custom_fields())", setup)

		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.add_update_custom_field #2026-01-04", patches)

	def test_the_patch_writes_the_flag_onto_the_row(self):
		self.assertEqual(FIELD, "Customer-customer_name_in_arabic")
		self.assertIn('frappe.db.set_value("Custom Field", FIELD, "reqd", 1)', self.source)

	def test_it_clears_the_doctype_cache(self):
		"""A meta still in cache goes on reporting the field as optional."""
		self.assertIn('frappe.clear_cache(doctype="Customer")', self.source)

	def test_it_checks_its_own_result(self):
		self.assertIn("frappe.throw(", self.source)

	def test_a_site_without_the_field_yet_is_left_alone(self):
		"""after_install will create it mandatory there, so there is nothing to correct."""
		self.assertIn('if not frappe.db.exists("Custom Field", FIELD):', self.source)

	def test_no_arabic_name_is_invented(self):
		"""211 of the 215 Customers have none. Mandatory bites on the next save of each,
		which is the point - an Arabic company name is the business's to supply."""
		self.assertNotIn("set_value(\n\t\t\"Customer\"", self.source)
		self.assertNotIn('"Customer", {', self.source)

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn(
			"one_fm.patches.v15_0.make_customer_arabic_name_mandatory", patches
		)
