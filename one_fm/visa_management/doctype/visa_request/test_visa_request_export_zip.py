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

	def test_each_request_gets_a_folder_with_its_visa_document(self):
		first, second = _seed("1"), _seed("2")
		file_one = _attach(first, "visa-one.txt", b"visa bytes one", "visa_document")
		file_two = _attach(second, "visa-two.txt", b"visa bytes two", "visa_document")

		archive, response = _export([first, second])

		self.assertEqual(response["type"], "download")
		self.assertEqual(response["filename"], "Visa Requests.zip")

		label = frappe.get_meta("Visa Request").get_label("visa_document")
		self.assertEqual(archive.read(f"{first}/{label} - {file_one.file_name}"), b"visa bytes one")
		self.assertEqual(archive.read(f"{second}/{label} - {file_two.file_name}"), b"visa bytes two")
		self.assertEqual(len(archive.namelist()), 2)

	def test_only_the_visa_document_is_exported(self):
		vr = _seed("1")
		_attach(vr, "passport.txt", b"passport bytes", "passport_copy")
		_attach(vr, "receipt.txt", b"receipt bytes", "payment_receipt")
		_attach(vr, "note.txt", b"sidebar bytes")
		# Frappe renames a file whose name is already on disk, so use the stored name.
		visa = _attach(vr, "visa.txt", b"visa bytes", "visa_document")

		archive, _response = _export([vr])

		label = frappe.get_meta("Visa Request").get_label("visa_document")
		expected = f"{vr}/{label} - {visa.file_name}"
		self.assertEqual(archive.namelist(), [expected])
		self.assertEqual(archive.read(expected), b"visa bytes")

	def test_a_request_without_a_visa_document_is_named_in_missing_files(self):
		with_doc, without_doc = _seed("1"), _seed("2")
		visa = _attach(with_doc, "visa.txt", b"visa bytes", "visa_document")
		_attach(without_doc, "passport.txt", b"passport bytes", "passport_copy")

		archive, _response = _export([with_doc, without_doc])

		label = frappe.get_meta("Visa Request").get_label("visa_document")
		names = archive.namelist()
		self.assertIn(f"{with_doc}/{label} - {visa.file_name}", names)
		self.assertFalse(any(n.startswith(without_doc + "/") for n in names))
		self.assertIn(
			f"{without_doc}: no Visa Document attached".encode(), archive.read("MISSING FILES.txt")
		)

	def test_a_visa_document_without_a_file_record_is_named_in_missing_files(self):
		orphan, good = _seed("1"), _seed("2")
		frappe.db.delete("File", _attach(orphan, "visa.txt", b"orphan bytes", "visa_document").name)
		_attach(good, "visa-good.txt", b"good bytes", "visa_document")

		archive, _response = _export([orphan, good])

		self.assertFalse(any(n.startswith(orphan + "/") for n in archive.namelist()))
		self.assertIn(
			f"{orphan}: Visa Document has no File record".encode(), archive.read("MISSING FILES.txt")
		)

	def test_the_archive_is_stored_not_compressed(self):
		vr = _seed("1")
		_attach(vr, "visa.txt", b"x" * 1000, "visa_document")

		archive, _response = _export([vr])

		for info in archive.infolist():
			self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

	def test_a_replaced_attachment_is_left_out(self):
		vr = _seed("1")
		old = _attach(vr, "old-visa.txt", b"old bytes", "visa_document")
		new = _attach(vr, "new-visa.txt", b"new bytes", "visa_document")

		archive, _response = _export([vr])

		label = frappe.get_meta("Visa Request").get_label("visa_document")
		names = archive.namelist()
		self.assertIn(f"{vr}/{label} - {new.file_name}", names)
		self.assertNotIn(f"{vr}/{label} - {old.file_name}", names)
		self.assertEqual(len(names), 1)

	def test_a_user_who_cannot_read_a_request_gets_permission_error(self):
		vr = _seed("1")
		_attach(vr, "visa.txt", b"secret", "visa_document")

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
		os.remove(_attach(vr, "visa.txt", b"gone", "visa_document").get_full_path())

		with self.assertRaises(frappe.ValidationError):
			export_zip(json.dumps([vr]))

	def test_a_partial_archive_lists_what_is_missing(self):
		vr = _seed("1")
		good = _seed("2")
		gone = _attach(vr, "visa.txt", b"gone", "visa_document")
		os.remove(gone.get_full_path())
		good_file = _attach(good, "visa-good.txt", b"still here", "visa_document")

		archive, _response = _export([vr, good])

		label = frappe.get_meta("Visa Request").get_label("visa_document")
		self.assertEqual(
			archive.read(f"{good}/{label} - {good_file.file_name}"), b"still here"
		)
		self.assertIn(gone.file_name.encode(), archive.read("MISSING FILES.txt"))

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
