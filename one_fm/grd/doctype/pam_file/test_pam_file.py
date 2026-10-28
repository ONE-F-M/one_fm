# -*- coding: utf-8 -*-
# Copyright (c) 2019, ONE FM and Contributors
# See license.txt
"""PAM File: validation and the derived active / inactive licence counts (WI-004135)."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

PAM_FILE_NAME = "_Test PAM File"
LICENSE_A = "_Test PAM A"
LICENSE_B = "_Test PAM B"


def licence_row(status, licence="_Test PAM X"):
	return {"civil_id_number_for_licensing": licence, "status": status}


def new_file(*rows):
	"""An unsaved PAM File with the given licence rows - no database involved."""
	doc = frappe.new_doc("PAM File")
	doc.pam_file_name = PAM_FILE_NAME
	for row in rows:
		doc.append("pam_licenses", row)
	return doc


def read_definition(*parts):
	return json.loads(
		frappe.read_file(frappe.get_app_path("one_fm", "grd", "doctype", *parts))
	)


def field_of(definition, fieldname):
	return next(f for f in definition["fields"] if f["fieldname"] == fieldname)


class TestPAMFile(FrappeTestCase):
	def tearDown(self):
		if frappe.db.exists("PAM File", PAM_FILE_NAME):
			frappe.delete_doc("PAM File", PAM_FILE_NAME, force=True)

	def get_doc(self):
		return frappe.get_doc({"doctype": "PAM File", "pam_file_name": PAM_FILE_NAME})

	def test_if_doc_exists(self):
		self.assertTrue(self.get_doc())

	def test_if_license_and_file_number_can_be_set_when_governent_project_is_False(self):
		doc = self.get_doc()
		doc.government_project = False
		doc.pam_file_number = 902100
		doc.file_number = 12345
		doc.license_number = 47
		doc.save()

		self.assertEqual(doc.license_number, "47")
		self.assertEqual(doc.file_number, "12345")

	def test_file_number_cannot_be_set_on_a_government_project(self):
		doc = self.get_doc()
		doc.government_project = True
		doc.file_number = 12345
		self.assertRaises(frappe.ValidationError, doc.save)


class TestSetLicenseCounts(FrappeTestCase):
	def test_active_and_inactive_rows_are_counted_apart(self):
		doc = new_file(
			licence_row("Active"), licence_row("Active"), licence_row("Inactive")
		)
		doc.set_license_counts()
		self.assertEqual(doc.number_of_active_licenses, "2")
		self.assertEqual(doc.number_of_inactive_licenses, "1")

	def test_suspended_and_blank_count_as_active(self):
		doc = new_file(licence_row("Suspended"), licence_row(""), licence_row(None))
		doc.set_license_counts()
		self.assertEqual(doc.number_of_active_licenses, "3")
		self.assertEqual(doc.number_of_inactive_licenses, "0")

	def test_an_empty_table_gives_zero_and_zero(self):
		doc = new_file()
		doc.number_of_active_licenses = "5"
		doc.number_of_inactive_licenses = "4"
		doc.set_license_counts()
		self.assertEqual(doc.number_of_active_licenses, "0")
		self.assertEqual(doc.number_of_inactive_licenses, "0")

	def test_a_row_with_no_licence_is_ignored(self):
		doc = new_file(
			licence_row("Active"),
			licence_row("Inactive", licence=None),
			licence_row("Active", licence=""),
		)
		doc.set_license_counts()
		self.assertEqual(doc.number_of_active_licenses, "1")
		self.assertEqual(doc.number_of_inactive_licenses, "0")

	def test_validate_recounts(self):
		doc = new_file(licence_row("Inactive"))
		doc.validate()
		self.assertEqual(doc.number_of_active_licenses, "0")
		self.assertEqual(doc.number_of_inactive_licenses, "1")


class TestLicenseCountsEndToEnd(FrappeTestCase):
	def setUp(self):
		self._cleanup()
		self.license_a = self._make_license(LICENSE_A, "_TEST-PAM-A", "Active")
		self.license_b = self._make_license(LICENSE_B, "_TEST-PAM-B", "Inactive")

		self.pam_file = new_file(
			licence_row("", self.license_a.name), licence_row("", self.license_b.name)
		)
		self.pam_file.insert()

	def tearDown(self):
		self._cleanup()

	def _cleanup(self):
		if frappe.db.exists("PAM File", PAM_FILE_NAME):
			frappe.delete_doc("PAM File", PAM_FILE_NAME, force=True)
		for name in (LICENSE_A, LICENSE_B):
			if frappe.db.exists("PAM License Details", name):
				frappe.delete_doc("PAM License Details", name, force=True)

	def _make_license(self, label, civil_id, status):
		return frappe.get_doc(
			{
				"doctype": "PAM License Details",
				"label_name": label,
				"civil_id_number_for_licensing": civil_id,
				"status": status,
			}
		).insert()

	def test_one_active_and_one_inactive_licence(self):
		self.pam_file.reload()
		self.assertEqual(self.pam_file.number_of_active_licenses, "1")
		self.assertEqual(self.pam_file.number_of_inactive_licenses, "1")

	def test_removing_a_row_and_saving_recounts(self):
		inactive_row = next(
			row for row in self.pam_file.pam_licenses if row.status == "Inactive"
		)
		self.pam_file.remove(inactive_row)
		self.pam_file.save()

		self.pam_file.reload()
		self.assertEqual(self.pam_file.number_of_active_licenses, "1")
		self.assertEqual(self.pam_file.number_of_inactive_licenses, "0")

	def test_a_licence_going_inactive_is_pushed_to_the_file(self):
		self.license_a.reload()
		self.license_a.status = "Inactive"
		self.license_a.save()

		self.pam_file.reload()
		self.assertEqual(self.pam_file.number_of_active_licenses, "0")
		self.assertEqual(self.pam_file.number_of_inactive_licenses, "2")
		row = next(
			r
			for r in self.pam_file.pam_licenses
			if r.civil_id_number_for_licensing == self.license_a.name
		)
		self.assertEqual(row.status, "Inactive")


class TestFieldsAreReadOnly(FrappeTestCase):
	def test_the_count_fields_are_read_only(self):
		definition = read_definition("pam_file", "pam_file.json")
		for fieldname in ("number_of_active_licenses", "number_of_inactive_licenses"):
			self.assertEqual(field_of(definition, fieldname).get("read_only"), 1, fieldname)

	def test_the_count_fields_stay_data(self):
		definition = read_definition("pam_file", "pam_file.json")
		for fieldname in ("number_of_active_licenses", "number_of_inactive_licenses"):
			self.assertEqual(field_of(definition, fieldname)["fieldtype"], "Data", fieldname)

	def test_the_row_status_is_read_only(self):
		definition = read_definition("pam_licenses", "pam_licenses.json")
		self.assertEqual(field_of(definition, "status").get("read_only"), 1)
