# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001977: reading the Visa Copy and the Payment Receipt into the Visa Request.

The two responses below are trimmed from the samples supplied with the work item - the
real shape Mindee returns for the ``e-visa`` and ``receipt`` models, including the
oddities the mapping has to survive: a reference number that arrives as a number, and
fields that come back with a null value.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.ocr_utils import (
	_PAYMENT_TIME,
	EVISA_FIELD_MAP,
	RECEIPT_FIELD_MAP,
	_merge_payment_time,
	parse_mindee_mapped_fields,
)
from one_fm.visa_management.doctype.visa_request.visa_request import (
	OCR_DOCUMENTS,
	_attachment_path,
)

EVISA_RESPONSE = {
	"gender": {"value": "Female"},
	"surnames": {"value": "TAMANG"},
	"given_names": {"value": "MENUKA"},
	"nationality": {"value": "NEPAL"},
	"date_of_birth": {"value": "1993-12-24"},
	"date_of_issue": {"value": "2026-01-19"},
	"date_of_expiry": {"value": "2026-04-18"},
	"place_of_birth": {"value": None},
	"passport_number": {"value": "PA4556704"},
	"visa_number": {"value": 283059338},
	"reference_number": {"value": 385515182},
}

RECEIPT_RESPONSE = {
	"date": {"value": "2026-01-19"},
	"time": {"value": "19:36:05"},
	"total_amount": {"value": 20},
	"receipt_number": {"value": "3028367"},
	"supplier_name": {"value": "Ministry of Interior"},
	"document_type": {"value": "expense_receipt"},
}


class TestTheMindeeMapping(FrappeTestCase):
	def test_the_visa_copy_gives_the_three_fields_the_work_item_asks_for(self):
		self.assertEqual(
			parse_mindee_mapped_fields(EVISA_RESPONSE, EVISA_FIELD_MAP),
			{
				"visa_reference_number": "283059338",
				"visa_issue_date": "2026-01-19",
				"visa_expiry_date": "2026-04-18",
			},
		)

	def test_the_visa_number_is_taken_and_not_the_reference(self):
		"""Settled in review: the visa carries both, and Visa Reference Number holds
		the Visa Number (283059338), not the Reference below it (385515182)."""
		parsed = parse_mindee_mapped_fields(EVISA_RESPONSE, EVISA_FIELD_MAP)

		self.assertEqual(parsed["visa_reference_number"], "283059338")
		self.assertNotIn("385515182", parsed.values())

	def test_the_payment_receipt_gives_the_date_and_the_time(self):
		"""Payment Date is a Datetime, and the receipt states the two separately."""
		self.assertEqual(
			_merge_payment_time(parse_mindee_mapped_fields(RECEIPT_RESPONSE, RECEIPT_FIELD_MAP)),
			{"payment_date": "2026-01-19 19:36:05"},
		)

	def test_a_receipt_with_no_time_still_gives_a_payment_date(self):
		"""It lands at midnight, which is what a Datetime does with a bare date."""
		response = dict(RECEIPT_RESPONSE, time={"value": None})

		self.assertEqual(
			_merge_payment_time(parse_mindee_mapped_fields(response, RECEIPT_FIELD_MAP)),
			{"payment_date": "2026-01-19"},
		)

	def test_the_time_carrier_never_reaches_the_document(self):
		"""It is not a Visa Request field; writing it would raise on save."""
		merged = _merge_payment_time(parse_mindee_mapped_fields(RECEIPT_RESPONSE, RECEIPT_FIELD_MAP))

		self.assertNotIn(_PAYMENT_TIME, merged)

	def test_a_numeric_visa_number_does_not_arrive_with_a_decimal_tail(self):
		"""The sample returns it as a number and the target is a Data field."""
		parsed = parse_mindee_mapped_fields(
			{"visa_number": {"value": 283059338.0}}, EVISA_FIELD_MAP
		)

		self.assertEqual(parsed["visa_reference_number"], "283059338")

	def test_nothing_is_taken_from_the_document_that_was_not_asked_for(self):
		"""The visa carries a passport number and a date of birth; neither is ours."""
		parsed = parse_mindee_mapped_fields(EVISA_RESPONSE, EVISA_FIELD_MAP)

		self.assertEqual(set(parsed), set(EVISA_FIELD_MAP.values()))

	def test_a_field_the_model_could_not_read_is_left_out(self):
		"""A partly-read visa is still worth showing; the operator fills the rest."""
		response = dict(EVISA_RESPONSE, date_of_expiry={"value": None})

		parsed = parse_mindee_mapped_fields(response, EVISA_FIELD_MAP)

		self.assertNotIn("visa_expiry_date", parsed)
		self.assertIn("visa_issue_date", parsed)

	def test_a_response_missing_the_field_entirely_does_not_raise(self):
		self.assertEqual(parse_mindee_mapped_fields({}, EVISA_FIELD_MAP), {})

	def test_the_mapping_only_fills_declared_visa_request_fields(self):
		"""A typo in a target fieldname would write nowhere and read as OCR failing."""
		meta = frappe.get_meta("Visa Request")
		targets = [
			f for f in list(EVISA_FIELD_MAP.values()) + list(RECEIPT_FIELD_MAP.values())
			if f != _PAYMENT_TIME
		]
		for fieldname in targets:
			self.assertIsNotNone(meta.get_field(fieldname), msg=fieldname)

	def test_payment_date_records_the_time_as_well(self):
		"""A Date field would silently drop the clock time off the receipt."""
		self.assertEqual(frappe.get_meta("Visa Request").get_field("payment_date").fieldtype, "Datetime")


# WI-002106 / AC 8: TestWhenTheOcrRuns was removed with queue_document_ocr(). The
# trigger is now a step in the Processa map - script task Activity_0ljbcgg - so what used
# to be tested here (the state guard, the changed-attachment check, the after-commit
# enqueue) has no code left to test. The step itself is covered by
# test_visa_request_bpmn_scripts.py::TestTheOcrScript.


class TestTheAttachmentPath(FrappeTestCase):
	def test_a_missing_file_is_reported_rather_than_read(self):
		with self.assertRaises(FileNotFoundError):
			_attachment_path("/files/does-not-exist-here.pdf")

	def test_no_attachment_is_an_error_not_a_silent_pass(self):
		with self.assertRaises(ValueError):
			_attachment_path("")

	def test_a_request_with_nothing_attached_is_skipped_quietly(self):
		"""Nothing to read, and nothing worth a traceback in the Error Log."""
		from unittest.mock import patch

		from one_fm.visa_management.doctype.visa_request.visa_request import run_document_ocr

		doc = frappe.new_doc("Visa Request")
		doc.visa_document = ""

		logged = []
		with patch.object(frappe, "get_doc", return_value=doc), patch.object(
			frappe, "log_error", side_effect=lambda **kw: logged.append(kw)
		), patch.object(frappe, "publish_realtime") as published:
			run_document_ocr("VR-TEST")

		self.assertEqual(logged, [])
		published.assert_not_called()

	def test_each_document_names_a_real_extractor(self):
		for fieldname, spec in OCR_DOCUMENTS.items():
			self.assertTrue(callable(frappe.get_attr(spec["extract"])), msg=fieldname)
