# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002745: the Employee carries the occupational sector of the PAM designation it holds."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields

FIELDNAME = "custom_occupational_sector"
SOURCE = "one_fm_pam_designation.occupational_sector"


def _field(fieldname):
	for fields in get_employee_custom_fields().values():
		for field in fields:
			if field["fieldname"] == fieldname:
				return field
	raise AssertionError(f"{fieldname} is not in the Employee custom field set")


class TestTheField(FrappeTestCase):
	def setUp(self):
		self.field = _field(FIELDNAME)

	def test_it_is_fetched_from_the_pam_designation(self):
		"""The sector is not on the employee - it is on the designation they hold - so a
		change of designation has to move it."""
		self.assertEqual(self.field["fetch_from"], SOURCE)

	def test_it_sits_beside_the_designation_it_comes_from(self):
		self.assertEqual(self.field["insert_after"], "one_fm_pam_designation")

	def test_it_is_a_copy_not_a_second_place_to_set_the_sector(self):
		"""A Link here would read as somewhere the sector can be decided; it cannot."""
		self.assertEqual(self.field["fieldtype"], "Data")

	def test_it_is_always_visible(self):
		"""The BA site's copy hides it unless Under Company Residency is ticked, which
		WI-002823 removes from every field on this form."""
		self.assertEqual(self.field.get("depends_on", ""), "")

	def test_it_is_labelled_the_way_pam_names_it(self):
		self.assertEqual(self.field["label"], "Occupational Sector")


class TestTheSourceItReads(FrappeTestCase):
	def test_the_designation_carries_an_occupational_sector(self):
		"""A fetch_from naming a field that does not exist copies nothing, silently."""
		field = frappe.get_meta("PAM Designation List").get_field("occupational_sector")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Occupational Sector")

	def test_the_designation_field_it_hangs_off_exists_on_employee(self):
		designation = _field("one_fm_pam_designation")
		self.assertEqual(designation["options"], "PAM Designation List")

	def test_the_two_halves_of_the_fetch_path_agree(self):
		"""`a.b` only works when `a` is the Link on Employee and `b` is a field on what it
		points at."""
		link, target = SOURCE.split(".")
		self.assertEqual(_field(link)["fieldname"], link)
		self.assertTrue(frappe.get_meta("PAM Designation List").get_field(target))


class TestItAgreesWithTheLicenceCounts(FrappeTestCase):
	def test_the_sector_is_still_reached_through_the_designation_for_counting(self):
		"""WI-002091 counts a licence's workers by joining Employee to PAM Designation
		List. This field is a copy for the form to show, not a second source of truth -
		the count must not start reading it, or a stale copy would change a headcount."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
			)
		)
		self.assertIn("Designation.occupational_sector == sector", source)
		self.assertNotIn(FIELDNAME, source)
