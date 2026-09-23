# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002823: the Employee fields Under Company Residency used to hide are always shown."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.patches.v15_0.clear_employee_residency_depends_on import GATED_FIELDS

GATE = "under_company_residency"


def _fixture_fields():
	return {
		field["fieldname"]: field
		for fields in get_employee_custom_fields().values()
		for field in fields
	}


class TestTheFixture(FrappeTestCase):
	def setUp(self):
		self.fields = _fixture_fields()

	def test_no_field_disappears_with_the_residency_box(self):
		"""An employee off the company's residency can still hold a PAM designation and
		still have a work permit expiring. Hiding those made the data invisible rather
		than absent."""
		gated = [
			fieldname
			for fieldname, field in self.fields.items()
			if GATE in (field.get("depends_on") or "")
		]
		self.assertEqual(gated, [])

	def test_the_seven_fields_the_story_is_about_are_all_in_the_fixture(self):
		"""A name that is not a field is a rule the patch silently skips."""
		for fieldname in GATED_FIELDS:
			self.assertIn(fieldname, self.fields, fieldname)

	def test_their_condition_is_emptied_rather_than_dropped(self):
		"""create_custom_fields only writes the keys it is handed, so a dropped key would
		leave the condition standing on every site that already has it."""
		for fieldname in GATED_FIELDS:
			self.assertEqual(self.fields[fieldname].get("depends_on"), "", fieldname)

	def test_the_gate_itself_never_had_a_condition(self):
		self.assertEqual(self.fields[GATE].get("depends_on"), "")

	def test_conditions_on_other_things_are_untouched(self):
		"""Only the residency gate is removed - the form still hides what it should."""
		other = [
			fieldname
			for fieldname, field in self.fields.items()
			if (field.get("depends_on") or "") and GATE not in field["depends_on"]
		]
		self.assertTrue(other, "every condition on the Employee form has been cleared")

	def test_a_mandatory_rule_that_is_not_about_residency_survives(self):
		"""one_fm_pam_designation is mandatory when a work permit is named. That is a
		different rule and this story does not touch it."""
		self.assertEqual(
			self.fields["one_fm_pam_designation"].get("mandatory_depends_on"), "work_permit"
		)


class TestThePatch(FrappeTestCase):
	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.clear_employee_residency_depends_on", patches)

	def test_it_checks_the_fixture_as_well_as_the_rows(self):
		"""Clearing the live rows without the fixture agreeing means the next migrate puts
		every condition straight back."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "clear_employee_residency_depends_on.py"
			)
		)
		self.assertIn("get_employee_custom_fields()", source)
		self.assertIn("would put it back", source)

	def test_it_writes_nothing_to_any_employee(self):
		"""The values were always there; only the form refused to draw them."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "clear_employee_residency_depends_on.py"
			)
		)
		self.assertNotIn('set_value("Employee"', source)
