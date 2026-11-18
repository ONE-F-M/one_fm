import os

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0 import delete_accommodation_inspection

PATCH = "one_fm.patches.v15_0.delete_accommodation_inspection"
KEPT = ("Accommodation Inspection Template", "Accommodation Inspection Parameter")


class TestDeleteAccommodationInspection(FrappeTestCase):
	"""The patch's table drop is DDL and commits; run on a throwaway site."""

	def assert_removed(self):
		for name in delete_accommodation_inspection.DOCTYPES:
			self.assertFalse(frappe.db.exists("DocType", name), name)
			self.assertIs(frappe.db.table_exists(name), False, name)

	def test_doctypes_and_tables_are_removed(self):
		self.assertEqual(
			delete_accommodation_inspection.DOCTYPES,
			("Accommodation Inspection", "Accommodation Inspection Reading"),
		)
		delete_accommodation_inspection.execute()
		self.assert_removed()

	def test_patch_is_idempotent(self):
		delete_accommodation_inspection.execute()
		delete_accommodation_inspection.execute()
		self.assert_removed()

	def test_template_and_parameter_are_not_in_scope(self):
		for name in KEPT:
			self.assertNotIn(name, delete_accommodation_inspection.DOCTYPES)

	def test_patch_is_registered_in_post_model_sync(self):
		path = os.path.join(os.path.dirname(frappe.get_app_path("one_fm")), "one_fm", "patches.txt")
		with open(path) as f:
			content = f.read()
		self.assertIn("[post_model_sync]", content)
		post = content.split("[post_model_sync]", 1)[1]
		lines = [line.split("#", 1)[0].strip() for line in post.splitlines()]
		self.assertIn(PATCH, lines)
		self.assertNotIn(PATCH, [line.split("#", 1)[0].strip() for line in content.split("[post_model_sync]", 1)[0].splitlines()])
