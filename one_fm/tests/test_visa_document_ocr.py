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
from frappe.utils import add_days

import one_fm.ocr_utils

from one_fm.ocr_utils import (
	_PAYMENT_TIME,
	EVISA_FIELD_MAP,
	RECEIPT_FIELD_MAP,
	_merge_payment_time,
	parse_mindee_mapped_fields,
)
from one_fm.visa_management.doctype.visa_request.visa_request import (
	OCR_DOCUMENTS,
	OCR_STATE,
	_attachment_path,
	discard_passport_dates,
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


class TestThePassportDatesAreNotTheVisaDates(FrappeTestCase):
	"""The e-visa prints the visa's Issue and Expiry in the header and the passport's own
	pair, unlabelled, under "Passport No.". The Mindee model has been returning the
	second, so a three-month visa was recorded as a ten-year one. These are the two
	checks that stop the wrong pair reaching the document while the model is corrected.
	"""

	def _doc(self, passport=("2021-03-08", "2031-03-07")):
		doc = frappe.new_doc("Visa Request")
		doc.passport_issued_on, doc.passport_expires_on = passport
		return doc

	def test_the_reported_case_is_refused(self):
		"""The dates written were the passport's, to the day."""
		extracted = {
			"visa_reference_number": "288853521",
			"visa_issue_date": "2021-03-08",
			"visa_expiry_date": "2031-03-07",
		}

		reason = discard_passport_dates(self._doc(), extracted)

		self.assertTrue(reason)
		self.assertEqual(extracted, {"visa_reference_number": "288853521"})

	def test_the_visa_s_own_dates_are_written(self):
		"""The same visa's real dates: issued 2026-09-14, expiring 2026-12-13."""
		extracted = {"visa_issue_date": "2026-09-14", "visa_expiry_date": "2026-12-13"}

		self.assertIsNone(discard_passport_dates(self._doc(), extracted))
		self.assertEqual(
			extracted, {"visa_issue_date": "2026-09-14", "visa_expiry_date": "2026-12-13"}
		)

	def test_a_ten_year_span_is_refused_even_without_the_passport_to_compare(self):
		"""A request whose applicant has no passport dates on file still gets the guard."""
		extracted = {"visa_issue_date": "2019-03-26", "visa_expiry_date": "2029-03-25"}

		reason = discard_passport_dates(self._doc(passport=(None, None)), extracted)

		self.assertTrue(reason)
		self.assertEqual(extracted, {})

	def test_one_matching_date_drops_both(self):
		"""Half a wrong pair is worse than none: it reads as a successful extraction."""
		extracted = {"visa_issue_date": "2021-03-08", "visa_expiry_date": "2026-12-13"}

		self.assertTrue(discard_passport_dates(self._doc(), extracted))
		self.assertEqual(extracted, {})

	def test_a_request_with_no_passport_dates_keeps_a_good_extraction(self):
		"""getdate() answers "today" for an empty value - two blanks must not match."""
		extracted = {"visa_issue_date": "2026-09-14", "visa_expiry_date": "2026-12-13"}

		self.assertIsNone(discard_passport_dates(self._doc(passport=(None, None)), extracted))

	def test_an_extraction_with_no_dates_in_it_is_left_alone(self):
		extracted = {"payment_date": "2026-09-14 16:27:47"}

		self.assertIsNone(discard_passport_dates(self._doc(), extracted))
		self.assertEqual(extracted, {"payment_date": "2026-09-14 16:27:47"})

	def test_a_visa_read_with_only_an_issue_date_is_still_offered(self):
		"""Nothing to compare the span against, and the issue date is not the passport's."""
		extracted = {"visa_issue_date": "2026-09-14"}

		self.assertIsNone(discard_passport_dates(self._doc(), extracted))

	def test_the_longest_visa_still_passes(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import MAX_VISA_VALIDITY_DAYS

		extracted = {
			"visa_issue_date": "2026-09-14",
			"visa_expiry_date": add_days("2026-09-14", MAX_VISA_VALIDITY_DAYS),
		}

		self.assertIsNone(discard_passport_dates(self._doc(passport=(None, None)), extracted))


class TestWhatTheOcrLeavesBehind(FrappeTestCase):
	"""db_set(update_modified=False) writes no Version, so without a comment
	nothing records that a value came off an attachment rather than an operator."""

	def _run(self, extracted, doc=None):
		from unittest.mock import patch

		from one_fm.visa_management.doctype.visa_request import visa_request
		from one_fm.visa_management.doctype.visa_request.visa_request import run_document_ocr

		doc = doc or frappe.new_doc("Visa Request")
		doc.workflow_state = OCR_STATE
		doc.visa_document = "/files/visa.pdf"
		doc.passport_issued_on, doc.passport_expires_on = "2021-03-08", "2031-03-07"
		doc.db_set = lambda *a, **kw: self.written.append(a[0])
		doc.add_comment = lambda comment_type, text: self.comments.append(text)

		self.written, self.comments = [], []
		with patch.object(frappe, "get_doc", return_value=doc), patch.object(
			visa_request, "_attachment_path", return_value="/files/visa.pdf"
		), patch.object(
			one_fm.ocr_utils, "extract_evisa_data", return_value=extracted
		), patch.object(frappe, "publish_realtime") as published:
			run_document_ocr("VR-TEST", ["visa_document"], user="Administrator")

		return published

	def test_what_was_read_is_named_on_the_timeline(self):
		self._run({"visa_issue_date": "2026-09-14", "visa_expiry_date": "2026-12-13"})

		self.assertEqual(len(self.comments), 1)
		self.assertIn("Visa Issue Date", self.comments[0])

	def test_the_refusal_is_recorded_and_nothing_is_written(self):
		published = self._run({"visa_issue_date": "2021-03-08", "visa_expiry_date": "2031-03-07"})

		self.assertEqual(self.written, [])
		self.assertIn("Please enter them from the visa", self.comments[0])
		self.assertTrue(published.call_args[0][1]["rejected"])

	def test_the_operator_is_told_the_dates_were_refused(self):
		"""The form would otherwise reload unchanged and read as the OCR finding nothing."""
		published = self._run({"visa_issue_date": "2021-03-08", "visa_expiry_date": "2031-03-07"})

		published.assert_called_once()
		self.assertEqual(published.call_args[0][1]["fields"], [])

	def test_the_reference_number_survives_a_refused_date_pair(self):
		"""The visa number comes off the header and was never in doubt."""
		self._run(
			{
				"visa_reference_number": "288853521",
				"visa_issue_date": "2021-03-08",
				"visa_expiry_date": "2031-03-07",
			}
		)

		self.assertEqual(self.written, [{"visa_reference_number": "288853521"}])
