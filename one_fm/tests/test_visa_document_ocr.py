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
	EVISA_FIELD_MAP,
	RECEIPT_FIELD_MAP,
	parse_mindee_mapped_fields,
)
from one_fm.visa_management.doctype.visa_request.visa_request import (
	OCR_DOCUMENTS,
	OCR_STATE,
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
				"visa_reference_number": "385515182",
				"visa_issue_date": "2026-01-19",
				"visa_expiry_date": "2026-04-18",
			},
		)

	def test_the_payment_receipt_gives_the_payment_date(self):
		self.assertEqual(
			parse_mindee_mapped_fields(RECEIPT_RESPONSE, RECEIPT_FIELD_MAP),
			{"payment_date": "2026-01-19"},
		)

	def test_a_numeric_reference_does_not_arrive_with_a_decimal_tail(self):
		"""The sample returns 385515182 as a number and the target is a Data field."""
		parsed = parse_mindee_mapped_fields(
			{"reference_number": {"value": 385515182.0}}, EVISA_FIELD_MAP
		)

		self.assertEqual(parsed["visa_reference_number"], "385515182")

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
		for fieldname in list(EVISA_FIELD_MAP.values()) + list(RECEIPT_FIELD_MAP.values()):
			self.assertIsNotNone(meta.get_field(fieldname), msg=fieldname)


class TestWhenTheOcrRuns(FrappeTestCase):
	"""The trigger, without calling Mindee."""

	def setUp(self):
		self.calls = []
		self._real_enqueue = frappe.enqueue
		frappe.enqueue = lambda *a, **kw: self.calls.append(kw)
		self.addCleanup(lambda: setattr(frappe, "enqueue", self._real_enqueue))

	def _doc(self, state=OCR_STATE, changed=("visa_document",), attached=("visa_document",)):
		doc = frappe.new_doc("Visa Request")
		doc.workflow_state = state
		for fieldname in attached:
			doc.set(fieldname, f"/files/{fieldname}.pdf")
		doc.has_value_changed = lambda fieldname: fieldname in changed
		return doc

	def _queue(self, doc):
		from one_fm.visa_management.doctype.visa_request.visa_request import queue_document_ocr

		doc.name = "VR-TEST"
		queue_document_ocr(doc)
		return self.calls

	def test_an_attachment_added_in_the_right_state_is_read(self):
		self.assertEqual(len(self._queue(self._doc())), 1)
		self.assertEqual(self.calls[0]["fieldnames"], ["visa_document"])

	def test_the_job_is_queued_only_after_the_save_commits(self):
		"""Reported from testing: the job ran and logged "No file attached" against a
		request that plainly had one. on_update runs inside the save transaction, so a
		worker picking the job up before the commit re-reads the document without the
		attachment on it."""
		self._queue(self._doc())

		self.assertTrue(self.calls[0].get("enqueue_after_commit"))

	def test_both_attachments_at_once_are_read_in_one_job(self):
		doc = self._doc(
			changed=("visa_document", "payment_receipt"),
			attached=("visa_document", "payment_receipt"),
		)

		self._queue(doc)

		self.assertEqual(sorted(self.calls[0]["fieldnames"]), ["payment_receipt", "visa_document"])

	def test_a_save_that_changed_no_attachment_reads_nothing(self):
		"""So an operator's correction to an extracted date is not overwritten."""
		self.assertEqual(self._queue(self._doc(changed=())), [])

	def test_another_state_reads_nothing(self):
		self.assertEqual(self._queue(self._doc(state="Draft")), [])

	def test_a_cleared_attachment_reads_nothing(self):
		self.assertEqual(self._queue(self._doc(attached=())), [])


class TestTheAttachmentPath(FrappeTestCase):
	def test_a_missing_file_is_reported_rather_than_read(self):
		with self.assertRaises(FileNotFoundError):
			_attachment_path("/files/does-not-exist-here.pdf")

	def test_no_attachment_is_an_error_not_a_silent_pass(self):
		with self.assertRaises(ValueError):
			_attachment_path("")

	def test_an_attachment_removed_before_the_job_runs_is_skipped_quietly(self):
		"""Nothing to read, and nothing worth a traceback in the Error Log."""
		from unittest.mock import patch

		from one_fm.visa_management.doctype.visa_request.visa_request import run_document_ocr

		doc = frappe.new_doc("Visa Request")
		doc.workflow_state = OCR_STATE
		doc.visa_document = ""

		logged = []
		with patch.object(frappe, "get_doc", return_value=doc), patch.object(
			frappe, "log_error", side_effect=lambda **kw: logged.append(kw)
		), patch.object(frappe, "publish_realtime") as published:
			run_document_ocr("VR-TEST", ["visa_document"], user="Administrator")

		self.assertEqual(logged, [])
		published.assert_not_called()

	def test_each_document_names_a_real_extractor(self):
		for fieldname, spec in OCR_DOCUMENTS.items():
			self.assertTrue(callable(frappe.get_attr(spec["extract"])), msg=fieldname)
