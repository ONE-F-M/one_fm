# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002102: the PAM License configuration migrated from the BA site.

Structure only - the compliance numbers are calculated by the work items stacked on top of
this one. What this holds is the shape they need: a license, its sector rows, and the two
links that say which sector an employee's designation falls in.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

NEW_DOCTYPES = ("Occupational Sector", "PAM License Details", "PAM License Stats", "PAM Licenses")

# Every link that holds the configuration together. One of these pointing at the wrong
# doctype and a license's numbers are counted against nothing.
LINKS = (
	("PAM License Stats", "occupational_sector", "Occupational Sector"),
	("PAM Designation List", "occupational_sector", "Occupational Sector"),
	("PAM License Details", "pam_license_stats", "PAM License Stats"),
	("PAM File", "pam_licenses", "PAM Licenses"),
	("PAM Licenses", "civil_id_number_for_licensing", "PAM License Details"),
)

# The per-sector figures the stacked work items fill in. Data fields, not numbers, which is
# how the BA site defines them - read through flt, written back as strings.
STATS_FIELDS = (
	"ratio_number_of_national_workers",
	"required_number_of_national_workers",
	"exceeding_the_ratio_number_of_national_workers",
	"exempt_number_of_workers",
	"violation_number_of_workers",
	"national_number_of_workers",
	"expatriate_number_of_workers",
	"status",
)


class TestPAMLicenseConfiguration(FrappeTestCase):
	def test_the_doctypes_exist(self):
		for doctype in NEW_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.db.exists("DocType", doctype))

	def test_the_child_tables_are_child_tables(self):
		for doctype in ("PAM License Stats", "PAM Licenses"):
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.get_meta(doctype).istable)

	def test_every_link_points_where_it_should(self):
		for doctype, fieldname, target in LINKS:
			with self.subTest(doctype=doctype, fieldname=fieldname):
				field = frappe.get_meta(doctype).get_field(fieldname)
				self.assertIsNotNone(field, f"{doctype} has no {fieldname}")
				self.assertEqual(field.options, target)

	def test_a_sector_row_carries_every_figure(self):
		meta = frappe.get_meta("PAM License Stats")
		for fieldname in STATS_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(meta.get_field(fieldname))

	def test_the_two_actual_counts_are_read_only(self):
		"""Derived from the employees on the license, never typed."""
		meta = frappe.get_meta("PAM License Stats")
		for fieldname in ("national_number_of_workers", "expatriate_number_of_workers"):
			with self.subTest(fieldname=fieldname):
				self.assertTrue(meta.get_field(fieldname).read_only)

	def test_the_pam_file_tracks_its_licenses(self):
		meta = frappe.get_meta("PAM File")
		for fieldname in ("file_status", "number_of_active_licenses", "number_of_inactive_licenses"):
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(meta.get_field(fieldname))

	def test_a_license_can_be_created_with_its_sector_rows(self):
		"""The shape end to end: a license, a sector, and a row joining them."""
		sector = _a_sector("_Test Occupational Sector")

		license = frappe.get_doc({
			"doctype": "PAM License Details",
			"label_name": "_Test PAM License",
			"civil_id_number_for_licensing": "1234567890",
			"license_name": "_Test License",
			"classification": "Commercial",
			"status": "Not suspended",
			"pam_license_stats": [{"occupational_sector": sector, "ratio_number_of_national_workers": "20"}],
		})
		license.flags.ignore_permissions = True
		license.insert()

		self.assertEqual(len(license.pam_license_stats), 1)
		self.assertEqual(license.pam_license_stats[0].occupational_sector, sector)


def _a_sector(name):
	if not frappe.db.exists("Occupational Sector", name):
		frappe.get_doc({"doctype": "Occupational Sector", "occupational_sector_type": name}).insert(
			ignore_permissions=True
		)
	return name
