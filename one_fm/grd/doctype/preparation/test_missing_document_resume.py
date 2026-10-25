# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""HD-1898774: a submit that was cut short has to be resumable.

PRE-ONB-2026-00008 submitted 27 Overseas rows. Each row opens six documents at about
four seconds, the whole set ran inside the submit request, and the web server killed the
request at its 120-second timeout part-way through row 24 - leaving three rows with no
documents, one row without its PCC Attestation, and nothing in the Error Log, because the
worker never got to the per-row `try`.

What these cover: creation is queued rather than run in the request, a second run opens
only the gaps, and the daily check names a batch that is short.
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	DOCUMENTS_CREATED_EVENT,
	INLINE_ROW_LIMIT,
	NEW_ACTION_DOCUMENTS,
	STEP_DOCTYPES,
	Preparation,
	category_for_action,
	create_documents_for_row,
	create_missing_documents,
	expected_steps_for_row,
	missing_steps_for_row,
	notify_preparations_with_missing_documents,
	rows_missing_documents,
)

OVERSEAS = "Overseas"


def _an_active_employee():
	"""An employee the GRD documents can be opened for.

	Work Permit refuses anyone inactive or with a relieving date. Taken from the site
	rather than created: Employee sits at MariaDB's row-size limit here.
	"""
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return frappe.get_doc("Employee", name)


class TestMissingDocumentResume(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"category": category_for_action(OVERSEAS),
				"posting_date": nowdate(),
				"preparation_record": [
					{"employee": self.employee.name, "renewal_or_extend": OVERSEAS}
				],
			}
		).insert(ignore_permissions=True)
		self.row = self.preparation.preparation_record[0]

	def _opened(self, doctype):
		return frappe.get_all(
			doctype, filters={"preparation": self.preparation.name}, pluck="name"
		)

	def test_an_overseas_row_owes_all_six_documents(self):
		"""The expectation and the plan are the same statement, read by three callers."""
		self.assertEqual(
			expected_steps_for_row(self.row), list(NEW_ACTION_DOCUMENTS[OVERSEAS].keys())
		)

	def test_a_renewal_row_owes_what_the_renewal_creators_open(self):
		"""The renewal path has no plan; the expectation mirrors its creators' conditions."""
		row = frappe._dict(
			{"employee": self.employee.name, "renewal_or_extend": "Renewal Expat", "nationality": "Indian"}
		)
		self.assertEqual(
			expected_steps_for_row(row),
			["work_permit", "medical_insurance", "residency", "paci"],
		)

	def test_a_kuwaiti_renewal_owes_only_a_work_permit(self):
		"""No residency, no civil ID application and no insurance process for a Kuwaiti."""
		row = frappe._dict(
			{"employee": self.employee.name, "renewal_or_extend": "Renewal (Kuwaiti)", "nationality": "Kuwaiti"}
		)
		self.assertEqual(expected_steps_for_row(row), ["work_permit"])

	def test_a_row_with_nothing_yet_is_missing_everything(self):
		self.assertEqual(
			missing_steps_for_row(self.row, self.preparation.name),
			expected_steps_for_row(self.row),
		)

	def test_a_complete_row_is_missing_nothing(self):
		create_documents_for_row(self.row, self.preparation.name)

		self.assertEqual(missing_steps_for_row(self.row, self.preparation.name), [])
		self.assertEqual(rows_missing_documents(self.preparation.name), [])

	def test_a_second_run_opens_nothing_twice(self):
		"""The whole point: the resume cannot duplicate the rows that did complete."""
		create_documents_for_row(self.row, self.preparation.name)
		opened = {doctype: self._opened(doctype) for doctype in STEP_DOCTYPES.values()}

		create_missing_documents(self.preparation.name)

		for doctype, names in opened.items():
			self.assertEqual(
				sorted(self._opened(doctype)), sorted(names), f"{doctype} was opened twice"
			)

	def test_the_gap_a_killed_run_left_is_filled(self):
		"""Row 24's case: everything but the last document, which the resume opens."""
		create_documents_for_row(self.row, self.preparation.name)
		pcc = self._opened("PCC Attestation")
		self.assertTrue(pcc)
		for name in pcc:
			frappe.delete_doc("PCC Attestation", name, force=True, ignore_permissions=True)

		self.assertEqual(missing_steps_for_row(self.row, self.preparation.name), ["pcc_attestation"])

		create_missing_documents(self.preparation.name)

		self.assertTrue(self._opened("PCC Attestation"))
		self.assertEqual(missing_steps_for_row(self.row, self.preparation.name), [])
		# And only the one document was opened - the other five were left alone.
		self.assertEqual(len(self._opened("Work Permit")), 1)

	def test_a_cancelled_document_is_not_reopened(self):
		"""An operator who cancelled one on purpose must not have it opened behind them."""
		create_documents_for_row(self.row, self.preparation.name)
		work_permit = self._opened("Work Permit")[0]
		frappe.db.set_value("Work Permit", work_permit, "workflow_state", "Cancelled")

		self.assertEqual(missing_steps_for_row(self.row, self.preparation.name), [])

		create_missing_documents(self.preparation.name)
		self.assertEqual(self._opened("Work Permit"), [work_permit])

	def test_the_row_stage_is_refreshed_by_the_resume(self):
		"""The blank Current Stage is what the ticket was raised about."""
		create_missing_documents(self.preparation.name)

		row = frappe.get_doc("Preparation", self.preparation.name).preparation_record[0]
		self.assertTrue(row.ref_doctype)
		self.assertTrue(row.ref_name)

	def test_the_inline_run_puts_the_stage_on_the_document_it_was_called_on(self):
		"""HD-1898774: the submit response is the only copy the browser gets.

		PRE-REN-2026-00010 wrote the Ref DocType of all 12 rows and the operator still saw
		blank cells, because db.set_value writes past the document the request is holding.
		"""
		self.preparation.enqueue_document_creation()

		row = self.preparation.preparation_record[0]
		self.assertTrue(row.ref_doctype, "the submit response carries a blank Ref DocType")
		self.assertTrue(row.ref_name)
		self.assertEqual(
			row.ref_doctype,
			frappe.db.get_value("Preparation Record", row.name, "ref_doctype"),
		)

	def test_a_run_tells_the_open_form_to_reload(self):
		"""The job's only route to a browser: nothing it writes moves the parent on disk."""
		published = []
		original = frappe.publish_realtime

		def record(event=None, message=None, **kwargs):
			published.append((event, message, kwargs))
			return None

		frappe.publish_realtime = record
		try:
			create_missing_documents(self.preparation.name)
		finally:
			frappe.publish_realtime = original

		events = [p for p in published if p[0] == DOCUMENTS_CREATED_EVENT]
		self.assertEqual(len(events), 1)
		_, message, kwargs = events[0]
		self.assertEqual(message["preparation"], self.preparation.name)
		self.assertEqual(kwargs["doctype"], "Preparation")
		self.assertEqual(kwargs["docname"], self.preparation.name)

	def test_the_form_listens_for_the_event_the_server_publishes(self):
		"""The two halves have to name the same event, and nothing checks that at runtime."""
		script = frappe.get_app_path(
			"one_fm", "grd", "doctype", "preparation", "preparation.js"
		)
		with open(script) as handle:
			source = handle.read()

		self.assertIn(f'frappe.realtime.on("{DOCUMENTS_CREATED_EVENT}"', source)
		self.assertIn("frm.reload_doc()", source)

	def test_a_batch_bigger_than_the_inline_limit_is_queued(self):
		"""The request timeout is the bug; a batch may not be opened inside the request."""
		source = inspect.getsource(Preparation.enqueue_document_creation)
		self.assertIn("frappe.enqueue", source)
		self.assertIn("create_missing_documents", source)
		self.assertIn("queue=\"long\"", source)

		submit = inspect.getsource(Preparation.on_submit)
		self.assertIn("enqueue_document_creation", submit)
		for creator in ("recall_create_work_permit_renewal", "recall_create_paci"):
			self.assertNotIn(creator, submit)

	def test_a_small_batch_is_opened_in_the_request(self):
		"""Ten rows is around forty seconds - the operator gets the result, not a notice."""
		queued = []
		original = frappe.enqueue

		def record(method, **kwargs):
			# Other jobs - a notification log, say - are nothing to do with this.
			if "create_missing_documents" in str(method):
				queued.append(kwargs)
			return None

		frappe.enqueue = record
		try:
			self.preparation.enqueue_document_creation()
		finally:
			frappe.enqueue = original

		self.assertEqual(queued, [])
		self.assertEqual(missing_steps_for_row(self.row, self.preparation.name), [])

	def test_a_large_batch_is_not_opened_in_the_request(self):
		"""Past the limit nothing is created inline - the job owns the whole batch."""
		queued = []
		original = frappe.enqueue

		def record(method, **kwargs):
			if "create_missing_documents" in str(method):
				queued.append(kwargs)
			return None

		frappe.enqueue = record
		self.preparation.preparation_record = [
			self.row for _ in range(INLINE_ROW_LIMIT + 1)
		]
		try:
			self.preparation.enqueue_document_creation()
		finally:
			frappe.enqueue = original

		self.assertEqual(len(queued), 1)
		self.assertEqual(queued[0]["preparation_name"], self.preparation.name)
		self.assertEqual(queued[0]["queue"], "long")
		self.assertEqual(self._opened("Work Permit"), [])

	def test_the_daily_check_names_a_batch_that_is_short(self):
		"""The safety net: nobody had to notice three blank cells for this to surface."""
		self.preparation.db_set("docstatus", 1, update_modified=False)
		self.preparation.db_set("grd_supervisor", "Administrator", update_modified=False)
		before = frappe.db.count("Notification Log", {"document_name": self.preparation.name})

		notify_preparations_with_missing_documents()

		self.assertGreater(
			frappe.db.count("Notification Log", {"document_name": self.preparation.name}), before
		)

	def test_the_daily_check_is_silent_about_a_complete_batch(self):
		"""A nightly mail about a batch with nothing wrong is noise nobody reads."""
		create_documents_for_row(self.row, self.preparation.name)
		self.preparation.db_set("docstatus", 1, update_modified=False)
		self.preparation.db_set("grd_supervisor", "Administrator", update_modified=False)
		before = frappe.db.count("Notification Log", {"document_name": self.preparation.name})

		notify_preparations_with_missing_documents()

		self.assertEqual(
			frappe.db.count("Notification Log", {"document_name": self.preparation.name}), before
		)
