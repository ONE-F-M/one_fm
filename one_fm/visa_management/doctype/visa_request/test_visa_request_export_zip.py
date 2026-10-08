# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Visa Request list view's standard filters and Export ZIP File action.

Requests are seeded straight into the table rather than inserted through the ORM: Visa
Request demands a passport, an eligible age and half a dozen other fields, and none of them
has anything to do with the export.
"""

import io
import json
import os
import zipfile

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.visa_management.doctype.visa_request.visa_request import (
	EXPORT_MAX_REQUESTS,
	export_zip,
)

SEEDED = "TEST-ZIP-VR-"
NO_ACCESS_USER = "zip-export-noaccess@example.com"


def _clear():
	frappe.db.delete("File", {"attached_to_doctype": "Visa Request", "attached_to_name": ["like", SEEDED + "%"]})
	frappe.db.delete("Visa Request", {"name": ["like", SEEDED + "%"]})


def _seed(suffix):
	doc = frappe.new_doc("Visa Request")
	doc.name = SEEDED + suffix
	doc.db_insert()
	return doc.name


def _attach(name, file_name, content, fieldname=None):
	"""A private File on the request; with fieldname it is the one that field points at."""
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "Visa Request",
			"attached_to_name": name,
			"attached_to_field": fieldname,
			"content": content,
			"is_private": 1,
		}
	)
	file.insert(ignore_permissions=True)
	if fieldname:
		frappe.db.set_value("Visa Request", name, fieldname, file.file_url)
	return file


def _export(names):
	export_zip(json.dumps(names))
	response = frappe.local.response
	return zipfile.ZipFile(io.BytesIO(response["filecontent"])), response


class TestVisaRequestExportZip(FrappeTestCase):
	def setUp(self):
		_clear()

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear()

	def test_each_request_gets_a_folder_with_its_attach_and_sidebar_files(self):
		first, second = _seed("1"), _seed("2")
		_attach(first, "passport-one.txt", b"passport bytes one", "passport_copy")
		_attach(first, "note-one.txt", b"sidebar bytes one")
		_attach(second, "passport-two.txt", b"passport bytes two", "passport_copy")
		_attach(second, "note-two.txt", b"sidebar bytes two")

		archive, response = _export([first, second])

		self.assertEqual(response["type"], "download")
		self.assertEqual(response["filename"], "Visa Requests.zip")

		names = archive.namelist()
		for vr in (first, second):
			self.assertTrue(any(n.startswith(vr + "/") for n in names), f"no folder for {vr}")

		label = frappe.get_meta("Visa Request").get_label("passport_copy")
		self.assertEqual(archive.read(f"{first}/{label} - passport-one.txt"), b"passport bytes one")
		self.assertEqual(archive.read(f"{first}/note-one.txt"), b"sidebar bytes one")
		self.assertEqual(archive.read(f"{second}/{label} - passport-two.txt"), b"passport bytes two")
		self.assertEqual(archive.read(f"{second}/note-two.txt"), b"sidebar bytes two")

	def test_the_archive_is_stored_not_compressed(self):
		vr = _seed("1")
		_attach(vr, "passport.txt", b"x" * 1000, "passport_copy")

		archive, _response = _export([vr])

		for info in archive.infolist():
			self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

	def test_a_replaced_attachment_is_left_out(self):
		vr = _seed("1")
		_attach(vr, "old-passport.txt", b"old bytes", "passport_copy")
		_attach(vr, "new-passport.txt", b"new bytes", "passport_copy")

		archive, _response = _export([vr])

		label = frappe.get_meta("Visa Request").get_label("passport_copy")
		names = archive.namelist()
		self.assertIn(f"{vr}/{label} - new-passport.txt", names)
		self.assertNotIn(f"{vr}/{label} - old-passport.txt", names)
		self.assertFalse(any("old-passport" in n for n in names))

	def test_a_user_who_cannot_read_a_request_gets_permission_error(self):
		vr = _seed("1")
		_attach(vr, "passport.txt", b"secret", "passport_copy")

		if not frappe.db.exists("User", NO_ACCESS_USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": NO_ACCESS_USER,
					"first_name": "No Access",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		frappe.set_user(NO_ACCESS_USER)
		with self.assertRaises(frappe.PermissionError):
			export_zip(json.dumps([vr]))

	def test_an_empty_list_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			export_zip(json.dumps([]))

	def test_nothing_readable_is_refused_instead_of_an_empty_zip(self):
		vr = _seed("1")
		os.remove(_attach(vr, "passport.txt", b"gone", "passport_copy").get_full_path())

		with self.assertRaises(frappe.ValidationError):
			export_zip(json.dumps([vr]))

	def test_a_partial_archive_lists_what_is_missing(self):
		vr = _seed("1")
		os.remove(_attach(vr, "passport.txt", b"gone", "passport_copy").get_full_path())
		_attach(vr, "note.txt", b"still here")

		archive, _response = _export([vr])

		self.assertEqual(archive.read(f"{vr}/note.txt"), b"still here")
		self.assertIn(b"passport.txt", archive.read("MISSING FILES.txt"))

	def test_more_than_the_cap_is_refused(self):
		names = [f"{SEEDED}{n}" for n in range(EXPORT_MAX_REQUESTS + 1)]
		self.assertEqual(len(names), 51)
		with self.assertRaises(frappe.ValidationError):
			export_zip(json.dumps(names))


class TestVisaRequestStandardFilters(FrappeTestCase):
	def test_meta_has_the_three_standard_filters(self):
		meta = frappe.get_meta("Visa Request")
		for fieldname in ("agency", "nationality", "workflow_state"):
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertIsNotNone(field, f"{fieldname} is not on Visa Request")
				self.assertTrue(field.in_standard_filter)
