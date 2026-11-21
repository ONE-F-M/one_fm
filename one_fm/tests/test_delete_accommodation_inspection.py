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
		with open(frappe.get_app_path("one_fm", "patches.txt")) as f:
			pre, post = f.read().split("[post_model_sync]", 1)

		def patch_names(block):
			return [line.split("#", 1)[0].strip() for line in block.splitlines()]

		self.assertIn(PATCH, patch_names(post))
		self.assertNotIn(PATCH, patch_names(pre))
