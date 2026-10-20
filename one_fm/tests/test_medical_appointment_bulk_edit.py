# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Bulk edit on the Medical Appointment list view."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.allow_medical_appointment_bulk_edit import execute, verify

DOCTYPE = "List View Settings"
LIST_VIEW = "Medical Appointment"


class TestMedicalAppointmentBulkEdit(FrappeTestCase):
	def setUp(self):
		# Rolled back by FrappeTestCase after the class, but keep each test independent.
		if frappe.db.exists(DOCTYPE, LIST_VIEW):
			frappe.delete_doc(DOCTYPE, LIST_VIEW, ignore_permissions=True, force=True)

	def test_the_patch_creates_the_record_with_allow_edit_on(self):
		self.assertFalse(frappe.db.exists(DOCTYPE, LIST_VIEW))
		execute()
		self.assertEqual(frappe.db.get_value(DOCTYPE, LIST_VIEW, "allow_edit"), 1)

	def test_the_patch_keeps_the_rest_of_an_existing_record(self):
		frappe.get_doc(
			{"doctype": DOCTYPE, "name": LIST_VIEW, "allow_edit": 0, "disable_count": 1}
		).insert(ignore_permissions=True)

		execute()

		values = frappe.db.get_value(
			DOCTYPE, LIST_VIEW, ["allow_edit", "disable_count"], as_dict=True
		)
		self.assertEqual(values.allow_edit, 1)
		self.assertEqual(values.disable_count, 1)

	def test_the_patch_can_run_twice(self):
		execute()
		execute()
		self.assertEqual(frappe.db.get_value(DOCTYPE, LIST_VIEW, "allow_edit"), 1)

	def test_verify_raises_when_the_flag_is_off(self):
		frappe.get_doc({"doctype": DOCTYPE, "name": LIST_VIEW, "allow_edit": 0}).insert(
			ignore_permissions=True
		)
		with self.assertRaises(frappe.ValidationError):
			verify()

	def test_medical_appointment_has_a_workflow_so_the_switch_is_needed(self):
		"""Frappe allows bulk edit outright on a DocType with no workflow, and hides it
		behind List View Settings.allow_edit on one that has."""
		self.assertTrue(
			frappe.db.exists("Workflow", {"document_type": LIST_VIEW, "is_active": 1}),
			f"{LIST_VIEW} has no active workflow - check whether the switch is still needed",
		)

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.allow_medical_appointment_bulk_edit", patches)
