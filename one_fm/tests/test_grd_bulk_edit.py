# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002887: bulk edit and inline editing on the four GRD list views."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.allow_bulk_edit_on_grd_list_views import LIST_VIEWS

FOLDERS = {
	"Work Permit": "work_permit",
	"Medical Insurance": "medical_insurance",
	"Residency": "residency",
	"PACI": "paci",
}


def _definition(folder):
	return json.loads(
		frappe.read_file(frappe.get_app_path("one_fm", "grd", "doctype", folder, f"{folder}.json"))
	)


def _fields(folder):
	return {f["fieldname"]: f for f in _definition(folder)["fields"]}


class TestTheSwitchIsTheRealOne(FrappeTestCase):
	def test_doctype_has_no_allow_edit_property(self):
		"""Setting it on a DocType JSON is dropped silently - DocType has no such field."""
		doctype_meta = json.loads(
			frappe.read_file(
				frappe.get_app_path("frappe", "core", "doctype", "doctype", "doctype.json")
			)
		)
		self.assertNotIn(
			"allow_edit", {f["fieldname"] for f in doctype_meta["fields"]}
		)

	def test_list_view_settings_is_where_allow_edit_lives(self):
		self.assertTrue(frappe.get_meta("List View Settings").get_field("allow_edit"))

	def test_no_grd_doctype_carries_the_phantom_key(self):
		for folder in FOLDERS.values():
			self.assertNotIn("allow_edit", _definition(folder), folder)

	def test_all_four_have_a_workflow_so_the_switch_is_needed(self):
		"""Frappe allows bulk edit outright on a DocType with no workflow, and hides it
		behind List View Settings.allow_edit on one that has."""
		for doctype in LIST_VIEWS:
			self.assertTrue(
				frappe.db.exists("Workflow", {"document_type": doctype, "is_active": 1}),
				f"{doctype} has no active workflow - check whether the switch is still needed",
			)

	def test_the_patch_covers_the_four_the_story_names(self):
		self.assertEqual(
			set(LIST_VIEWS), {"Work Permit", "Medical Insurance", "Residency", "PACI"}
		)

	def test_the_patch_keeps_the_rest_of_an_existing_record(self):
		"""List View Settings also holds the operator's column choices; a fixture would
		overwrite those on every migrate."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "allow_bulk_edit_on_grd_list_views.py"
			)
		)
		self.assertIn('frappe.db.set_value(DOCTYPE, doctype, "allow_edit", 1)', source)
		self.assertIn("continue", source)

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.allow_bulk_edit_on_grd_list_views", patches)


class TestTheFieldsTheStoryNames(FrappeTestCase):
	"""Bulk edit offers a field only when it is not hidden, read-only or virtual, and the
	Report View makes the same fields editable in place."""

	def test_date_of_application_is_editable_on_all_four(self):
		for doctype, folder in FOLDERS.items():
			field = _fields(folder)["date_of_application"]
			self.assertNotEqual(field.get("read_only"), 1, doctype)
			self.assertNotEqual(field.get("hidden"), 1, doctype)

	def test_the_pro_user_field_is_editable_and_in_the_list_where_it_exists(self):
		field = _fields("paci")["pro_user"]
		self.assertNotEqual(field.get("read_only"), 1)
		self.assertEqual(field["in_list_view"], 1)

	def test_the_doctypes_without_a_pro_user_field_are_left_alone(self):
		"""Work Permit and Medical Insurance have no such field, and Residency's arrives
		with WI-002495. None is invented here."""
		for folder in ("work_permit", "medical_insurance"):
			self.assertNotIn("pro_user", _fields(folder), folder)


class TestWhatWasNotAskedFor(FrappeTestCase):
	"""grd_operator is filled from HR Settings' default_grd_operator on validate. The
	story names PRO User and Date of Application; unhiding and unlocking a system-set
	field is neither."""

	def test_it_is_still_read_only_everywhere(self):
		for doctype, folder in FOLDERS.items():
			self.assertEqual(_fields(folder)["grd_operator"].get("read_only"), 1, doctype)

	def test_it_is_still_hidden_where_it_was(self):
		for folder in ("medical_insurance", "paci"):
			self.assertEqual(_fields(folder)["grd_operator"].get("hidden"), 1, folder)

	def test_it_was_not_added_to_any_list_view(self):
		for doctype, folder in FOLDERS.items():
			self.assertNotEqual(
				_fields(folder)["grd_operator"].get("in_list_view"), 1, doctype
			)

	def test_the_controllers_still_fill_it_in(self):
		for folder in ("work_permit", "residency", "paci"):
			source = frappe.read_file(
				frappe.get_app_path("one_fm", "grd", "doctype", folder, f"{folder}.py")
			)
			self.assertIn("default_grd_operator", source, folder)
