# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002233: every Link that named a PAM File names the licence instead."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.repoint_pam_file_links_to_license_details import (
	FETCH_FIELDS,
	LINK_FIELDS,
	TARGET,
)


class TestPAMFileLinkMigration(FrappeTestCase):
	def test_every_link_points_at_the_licence(self):
		for doctype, fieldname in LINK_FIELDS:
			with self.subTest(field=f"{doctype}.{fieldname}"):
				field = frappe.get_meta(doctype).get_field(fieldname)
				self.assertIsNotNone(field)
				self.assertEqual(field.options, TARGET)

	def test_nothing_is_left_pointing_at_the_file(self):
		"""The list above is the whole set - a Link to PAM File added anywhere else, or one
		this patch missed, names itself here rather than going unnoticed."""
		remaining = frappe.get_all(
			"DocField", filters={"fieldtype": "Link", "options": "PAM File"}, fields=["parent", "fieldname"]
		) + frappe.get_all(
			"Custom Field", filters={"fieldtype": "Link", "options": "PAM File"}, fields=["dt as parent", "fieldname"]
		)
		# PAM File amends itself; that Link is the doctype's own and is not a reference to
		# licence information.
		remaining = [row for row in remaining if (row.parent, row.fieldname) != ("PAM File", "amended_from")]
		self.assertEqual(remaining, [])

	def test_the_pam_number_is_fetched_from_the_licence(self):
		"""The file states the number as pam_file_number and the licence as
		civil_id_number_for_licensing, so the fetch has to move with the link or it reads a
		field the licence does not have."""
		for doctype, fieldname, fetch_from in FETCH_FIELDS:
			with self.subTest(field=f"{doctype}.{fieldname}"):
				self.assertEqual(frappe.get_meta(doctype).get_field(fieldname).fetch_from, fetch_from)

	def test_the_licence_carries_the_number_the_fetches_name(self):
		self.assertIsNotNone(
			frappe.get_meta(TARGET).get_field("civil_id_number_for_licensing")
		)

	def test_a_dangling_link_does_not_blank_the_number_beside_it(self):
		"""Existing values are PAM File names and are not migrated - a file can carry more
		than one licence, so there is nothing to map them to. Frappe skips the fetch when a
		link does not resolve, so the number an employee already carries survives the change
		rather than being wiped on the next save. The licence headcounts (WI-002091) and four
		downstream fetches all read that number."""
		certificate = frappe.new_doc("PAM Salary Certificate")
		certificate.pam_file_name = "_Test Licence That Does Not Exist"
		certificate.pam_file_number = "2921143"
		certificate.get_invalid_links()

		self.assertEqual(certificate.pam_file_number, "2921143")
