# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.subcontract.doctype.subcontract_staff_shortlist_detail.subcontract_staff_shortlist_detail import (
	trigger_ocr,
)

MODULE = "one_fm.subcontract.doctype.subcontract_staff_shortlist_detail.subcontract_staff_shortlist_detail"


def file_at(*parts):
	"""A File whose full path is the given site path."""
	file_doc = MagicMock()
	file_doc.get_full_path.return_value = frappe.get_site_path(*parts)
	return patch("frappe.get_doc", return_value=file_doc)


class TestTriggerOcr(FrappeTestCase):
	def test_non_civil_id_is_skipped(self):
		self.assertEqual(trigger_ocr("/files/id.jpg", "Visa Copy")["message"], "OCR is only triggered for Civil ID type")

	def test_url_without_file_record_is_not_found(self):
		with patch("frappe.get_all", return_value=[]), patch(f"{MODULE}.extract_kuwait_civil_id_data") as ocr:
			result = trigger_ocr("/files/../../site_config.json", "Civil ID")
		self.assertEqual(result["message"], "File not found")
		ocr.assert_not_called()

	def test_file_the_caller_cannot_read_is_refused(self):
		with patch("frappe.get_all", return_value=["F-1"]), \
			patch("frappe.has_permission", return_value=False), \
			patch(f"{MODULE}.extract_kuwait_civil_id_data") as ocr, \
			self.assertRaises(frappe.PermissionError):
			trigger_ocr("/private/files/id.jpg", "Civil ID")
		ocr.assert_not_called()

	def test_path_outside_the_files_folders_is_refused(self):
		with patch("frappe.get_all", return_value=["F-1"]), \
			patch("frappe.has_permission", return_value=True), \
			file_at("public", "files", "..", "..", "site_config.json"), \
			patch(f"{MODULE}.extract_kuwait_civil_id_data") as ocr, \
			self.assertRaises(frappe.PermissionError):
			trigger_ocr("/files/../../site_config.json", "Civil ID")
		ocr.assert_not_called()

	def test_readable_file_is_read(self):
		extracted = {"civil_id_no": "123456789012", "expiry_date": "2030-01-01", "birth_date": "1990-01-01"}
		with patch("frappe.get_all", return_value=["F-1"]), \
			patch("frappe.has_permission", return_value=True), \
			file_at("private", "files", "id.jpg"), \
			patch("os.path.exists", return_value=True), \
			patch(f"{MODULE}.extract_kuwait_civil_id_data", return_value=extracted) as ocr:
			result = trigger_ocr("/private/files/id.jpg", "Civil ID")
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["civil_id_no"], "123456789012")
		self.assertEqual(result["data"]["civil_id_expiry_date"], "2030-01-01")
		self.assertTrue(ocr.call_args[0][0].endswith("/private/files/id.jpg"))
