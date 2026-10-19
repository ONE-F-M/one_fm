# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Reading the Payment Date from receipt PDFs. Synthetic text only: real receipts hold personal data."""

import io
import unicodedata

import frappe
from frappe.tests.utils import FrappeTestCase
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from one_fm.grd.doctype.paci.paci import create_PACI
from one_fm.grd.doctype.paci.test_payment_date import _an_active_employee
from one_fm.grd.payment_receipt import (
	PAM_KNET_HEADING,
	payment_date_from_text,
	read_payment_date,
	receipt_text,
)

# The K-Net heading as pypdf returns it: Arabic presentation forms.
PAM_KNET_HEADING_GLYPHS = (
	"ﺕﻑﺍﺹﻱﻝ ﺩﻑﻉ ﻉﻥ "
	"ﻁﺭﻱﻕ ﺍﻝﻙﻱ ﻥﺕ"
)


def _pdf(*lines: str) -> bytes:
	"""A one-page text PDF with each line in Helvetica."""
	writer = PdfWriter()
	page = writer.add_blank_page(400, 400)
	font = DictionaryObject({
		NameObject("/Type"): NameObject("/Font"),
		NameObject("/Subtype"): NameObject("/Type1"),
		NameObject("/BaseFont"): NameObject("/Helvetica"),
	})
	page[NameObject("/Resources")] = DictionaryObject({
		NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
	})
	body = " 0 -20 Td ".join(f"({line}) Tj" for line in lines)
	stream = DecodedStreamObject()
	stream.set_data(f"BT /F1 12 Tf 10 300 Td {body} ET".encode())
	page[NameObject("/Contents")] = writer._add_object(stream)
	buffer = io.BytesIO()
	writer.write(buffer)
	return buffer.getvalue()


class TestPaymentDateFromText(FrappeTestCase):
	def test_paci_reads_the_value_after_the_label(self):
		text = "Payment Date\n05/10/2026 09:29 AMReference No 123"
		self.assertEqual(payment_date_from_text("PACI", text), "2026-10-05 09:29:00")

	def test_moh_reads_a_dot_separated_time(self):
		text = "Health Insurance\n06/10/2026 10.52 PM\nAmount 50.000"
		self.assertEqual(payment_date_from_text("Medical Insurance", text), "2026-10-06 22:52:00")

	def test_moi_reads_time_then_date_with_or_without_spaces(self):
		for text in ("Date & Time 19:40:31-2026-10-04", "تاريخ ووقت العملية\n19:39:18 - 2026-10-04"):
			with self.subTest(text=text):
				self.assertTrue(payment_date_from_text("Residency", text).startswith("2026-10-04 19:"))
		self.assertEqual(payment_date_from_text("Residency", "19:40:31-2026-10-04"), "2026-10-04 19:40:31")

	def test_pam_reads_the_knet_date_not_the_later_print_date(self):
		text = (
			f"{PAM_KNET_HEADING}\nDate/Time: 30/07/2026 12:14 PM627770007812916\nDate / Time\n"
			"تاريخ الطباعة 09/08/2026 10:06 PM"
		)
		self.assertEqual(payment_date_from_text("Work Permit", text), "2026-07-30 12:14:00")

	def test_pam_skips_a_print_date_before_the_knet_section(self):
		text = f"تاريخ الطباعة 09/08/2026 10:06 PM\n{PAM_KNET_HEADING}\n04/10/2026 4:39 PM627770007812916"
		self.assertEqual(payment_date_from_text("Work Permit", text), "2026-10-04 16:39:00")

	def test_pam_heading_matches_only_after_nfkc(self):
		text = f"{PAM_KNET_HEADING_GLYPHS}\n04/10/2026 4:39 PM627770007812916"
		self.assertIsNone(payment_date_from_text("Work Permit", text))
		self.assertEqual(
			payment_date_from_text("Work Permit", unicodedata.normalize("NFKC", text)), "2026-10-04 16:39:00"
		)

	def test_pam_without_the_heading_is_none(self):
		self.assertIsNone(payment_date_from_text("Work Permit", "09/08/2026 10:06 PM"))

	def test_no_anchor_or_empty_text_is_none(self):
		for doctype in ("PACI", "Work Permit", "Medical Insurance", "Residency"):
			for text in ("", "Receipt with no date", "Payment Date pending"):
				with self.subTest(doctype=doctype, text=text):
					self.assertIsNone(payment_date_from_text(doctype, text))

	def test_receipt_text_reads_a_text_pdf(self):
		text = receipt_text(_pdf("Payment Date", "05/10/2026 09:29 AM"))
		self.assertEqual(payment_date_from_text("PACI", text), "2026-10-05 09:29:00")


class TestReadPaymentDate(FrappeTestCase):
	def setUp(self):
		self.paci = create_PACI(frappe.get_doc("Employee", _an_active_employee()), "Renewal")

	def _attach(self, content: bytes, file_name: str = "receipt.pdf"):
		file = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "PACI",
			"attached_to_name": self.paci.name,
			"attached_to_field": "upload_civil_id_payment",
		}).insert(ignore_permissions=True)
		self.addCleanup(file.delete, ignore_permissions=True)
		return file

	def test_reads_an_attached_receipt(self):
		file = self._attach(_pdf("Payment Date", "05/10/2026 09:29 AMReference No"))
		self.assertEqual(read_payment_date("PACI", self.paci.name, file.file_url), "2026-10-05 09:29:00")

	def test_a_file_that_is_not_a_pdf_is_none(self):
		# An image upload: Frappe refuses an invalid file named .pdf before we see it.
		file = self._attach(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, file_name="receipt.png")
		self.assertIsNone(read_payment_date("PACI", self.paci.name, file.file_url))

	def test_a_file_attached_elsewhere_is_none(self):
		self.assertIsNone(read_payment_date("PACI", self.paci.name, "/private/files/not-attached-here.pdf"))

	def test_a_user_without_write_is_refused(self):
		file = self._attach(_pdf("Payment Date", "05/10/2026 09:29 AM"))
		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, read_payment_date, "PACI", self.paci.name, file.file_url)

	def test_another_doctype_is_refused(self):
		self.assertRaises(frappe.ValidationError, read_payment_date, "User", "Administrator", "/files/x.pdf")
