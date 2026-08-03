# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Reaching the published document from the Document Request that produced it.

``document_link`` on the request holds the URL and is the only thing the form
reads. These tests cover the two properties around it:

  * it is preferred over every other source, with no lookups at all; and
  * when it is empty, the link is recovered and **written into it**, so the
    recovery happens once per request rather than on every view.

Recovery has two sources, in order of authority — the Document Register entry,
then the BPMN run's task data. It exists because ``update_field`` writes the
published status with ``frappe.db.set_value``, so no doc hook fires at publish;
without it, every document published before this field existed is unreachable.
"""

import json
import unittest

import frappe

from one_fm.one_fm.doctype.document_request.document_request import (
	get_published_document_link,
)

FILE_ID = "_TestDriveFileId0000000000001"
WEB_VIEW_LINK = f"https://docs.google.com/document/d/{FILE_ID}/edit?usp=drivesdk"


class DocumentRequestFixtures:
	"""Shared fixtures.

	Deliberately not a TestCase — a TestCase base would have every one of its
	tests re-run by each subclass.
	"""

	def setUp(self):
		self.requester = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.requester:
			self.skipTest("no active Employee to raise a request as")

	def tearDown(self):
		frappe.db.rollback()

	# --- fixtures ----------------------------------------------------------

	def _request(self, status="Published", reference_document=None, document_link=None):
		doc = frappe.get_doc({
			"doctype": "Document Request",
			"requester": self.requester,
			"request_action": "Create",
			"document_type": "SOP",
			"title": "_Test Link Resolution",
			"requirement_text": "x",
		})
		doc.insert(ignore_permissions=True)
		# status is read-only and normally driven by the process; set it the way
		# the map does — straight to the database, no hooks.
		frappe.db.set_value("Document Request", doc.name, "status", status, update_modified=False)
		if reference_document:
			frappe.db.set_value(
				"Document Request",
				doc.name,
				"reference_document",
				reference_document,
				update_modified=False,
			)
		if document_link:
			frappe.db.set_value(
				"Document Request",
				doc.name,
				"document_link",
				document_link,
				update_modified=False,
			)
		return doc.name

	def _stored_link(self, request):
		return frappe.db.get_value("Document Request", request, "document_link")

	def _index_entry(self, link=WEB_VIEW_LINK, file_id=FILE_ID):
		entry = frappe.get_doc({
			"doctype": "Document Register",
			"drive_file_id": file_id,
			"title": "_Test Indexed Document",
			"document_type": "SOP",
			"drive_file_link": link,
		})
		entry.insert(ignore_permissions=True)
		return entry.name

	def _instance_with_drive_file(self, request, drive_file):
		"""A completed run carrying whatever the Drive connector returned."""
		instance = frappe.get_doc({
			"doctype": "BPMN Process Instance",
			"process_model": "Document Request",
			"context_doctype": "Document Request",
			"context_docname": request,
			"status": "Completed",
		})
		instance.insert(ignore_permissions=True)
		frappe.db.set_value(
			"BPMN Process Instance",
			instance.name,
			"workflow_state",
			json.dumps({"data": {"drive_file": drive_file}}),
			update_modified=False,
		)
		return instance.name


class TestStoredFieldIsTheReadPath(DocumentRequestFixtures, unittest.TestCase):
	"""`document_link` is what the form reads; everything else is recovery."""

	STORED = "https://docs.google.com/document/d/_stored_/edit"

	def test_the_stored_field_is_returned(self):
		request = self._request(document_link=self.STORED)

		link = get_published_document_link(request)

		self.assertEqual(link["url"], self.STORED)
		self.assertEqual(link["source"], "document_link")

	def test_the_stored_field_beats_both_recovery_sources(self):
		"""Once stored, nothing else is consulted — so a document moved in Drive
		keeps the link the request was published with rather than silently
		following an index entry that was updated by a later request."""
		request = self._request(
			document_link=self.STORED, reference_document=self._index_entry()
		)
		self._instance_with_drive_file(request, {"id": FILE_ID, "webViewLink": WEB_VIEW_LINK})

		self.assertEqual(get_published_document_link(request)["url"], self.STORED)

	def test_recovery_writes_the_link_into_the_field(self):
		"""The point of recovery: it happens once per request, not per view."""
		request = self._request(reference_document=self._index_entry())
		self.assertIsNone(self._stored_link(request))

		first = get_published_document_link(request)

		self.assertEqual(first["source"], "reference_document")
		self.assertEqual(self._stored_link(request), WEB_VIEW_LINK)

		# Second call now takes the cheap path.
		self.assertEqual(get_published_document_link(request)["source"], "document_link")

	def test_recovery_from_the_run_also_writes_the_field(self):
		request = self._request()
		self._instance_with_drive_file(request, {"id": FILE_ID, "webViewLink": WEB_VIEW_LINK})

		self.assertEqual(get_published_document_link(request)["source"], "process_instance")
		self.assertEqual(self._stored_link(request), WEB_VIEW_LINK)

	def test_recovery_does_not_bump_the_modified_timestamp(self):
		"""The field is derived and read-only. Bumping `modified` would give
		anyone with the form open a stale-document error in exchange for a
		cached URL, and would add a Version row for a value nobody typed."""
		request = self._request(reference_document=self._index_entry())
		before = frappe.db.get_value("Document Request", request, "modified")

		get_published_document_link(request)

		self.assertEqual(frappe.db.get_value("Document Request", request, "modified"), before)

	def test_nothing_is_stored_when_there_is_nothing_to_store(self):
		request = self._request()

		self.assertEqual(get_published_document_link(request), {})
		self.assertIsNone(self._stored_link(request))

	def test_a_withdrawn_requests_link_is_resolved_and_stored(self):
		"""Withdrawal keeps the document, so the link is still worth having.

		This used to assert the opposite, back when the Delete branch trashed the
		Drive file and resolving the link handed back a URL to something gone. A
		Delete request now marks the document inactive and revokes its sharing;
		the file, its content and its versions are all kept. Refusing to resolve
		the link would leave an auditor reading "withdrawn" with no way to see
		*what* was withdrawn.
		"""
		entry = self._index_entry()
		frappe.db.set_value("Document Register", entry, "lifecycle_state", "Inactive")
		request = self._request(status="Deleted", reference_document=entry)

		link = get_published_document_link(request)

		self.assertEqual(link["url"], WEB_VIEW_LINK)
		self.assertEqual(link["lifecycle"], "Inactive")
		self.assertEqual(self._stored_link(request), WEB_VIEW_LINK)


class TestLinkResolution(DocumentRequestFixtures, unittest.TestCase):
	# --- preferred source --------------------------------------------------

	def test_link_comes_from_the_index_entry_when_present(self):
		request = self._request(reference_document=self._index_entry())

		link = get_published_document_link(request)

		self.assertEqual(link["url"], WEB_VIEW_LINK)
		self.assertEqual(link["source"], "reference_document")
		self.assertEqual(link["title"], "_Test Indexed Document")

	def test_the_index_entry_wins_over_the_run(self):
		"""Both routes available: the canonical record is the one used."""
		request = self._request(reference_document=self._index_entry())
		self._instance_with_drive_file(
			request, {"id": "other", "webViewLink": "https://example.invalid/stale"}
		)

		self.assertEqual(get_published_document_link(request)["source"], "reference_document")

	# --- fallback ----------------------------------------------------------

	def test_falls_back_to_the_run_that_created_the_file(self):
		"""The case every already-published document is in."""
		request = self._request()
		self._instance_with_drive_file(request, {"id": FILE_ID, "webViewLink": WEB_VIEW_LINK})

		link = get_published_document_link(request)

		self.assertEqual(link["url"], WEB_VIEW_LINK)
		self.assertEqual(link["source"], "process_instance")

	def test_a_run_recording_only_a_file_id_still_resolves(self):
		"""Older runs stored the id without the webViewLink."""
		request = self._request()
		self._instance_with_drive_file(request, {"id": FILE_ID})

		self.assertEqual(
			get_published_document_link(request)["url"],
			f"https://docs.google.com/document/d/{FILE_ID}/edit",
		)

	def test_an_index_entry_without_a_link_falls_through_to_the_run(self):
		"""A half-written entry must not shadow a usable link."""
		request = self._request(reference_document=self._index_entry(link=""))
		self._instance_with_drive_file(request, {"id": FILE_ID, "webViewLink": WEB_VIEW_LINK})

		self.assertEqual(get_published_document_link(request)["source"], "process_instance")

	# --- nothing to show ---------------------------------------------------

	def test_no_link_when_the_run_recorded_no_file(self):
		request = self._request()
		self._instance_with_drive_file(request, {})

		self.assertEqual(get_published_document_link(request), {})

	def test_no_link_when_there_is_no_run_at_all(self):
		self.assertEqual(get_published_document_link(self._request()), {})

	def test_a_withdrawn_request_still_offers_its_link(self):
		"""Nothing was deleted, so there is something to open — and it says so.

		The interesting half is ``lifecycle``: the caller has to be able to tell
		"here is the document" from "here is a document nobody should be
		following any more", and the URL alone cannot carry that.
		"""
		entry = self._index_entry()
		frappe.db.set_value("Document Register", entry, "lifecycle_state", "Inactive")
		request = self._request(status="Deleted", reference_document=entry)

		link = get_published_document_link(request)

		self.assertEqual(link["url"], WEB_VIEW_LINK)
		self.assertEqual(link["lifecycle"], "Inactive")

	def test_an_active_documents_link_reports_it_as_active(self):
		request = self._request(reference_document=self._index_entry())

		self.assertEqual(get_published_document_link(request)["lifecycle"], "Active")

	def test_a_rejected_request_offers_no_link(self):
		request = self._request(status="Request Rejected")
		self._instance_with_drive_file(request, {"id": FILE_ID, "webViewLink": WEB_VIEW_LINK})

		self.assertEqual(get_published_document_link(request), {})

	def test_unknown_request_returns_nothing_rather_than_raising(self):
		self.assertEqual(get_published_document_link("DOC-REQ-does-not-exist"), {})

	def test_workflow_state_cannot_hold_malformed_json(self):
		"""Why the parse guard is belt-and-braces rather than load-bearing.

		The column carries a JSON check constraint, so malformed text cannot be
		stored at all — the guard exists for an empty/NULL state, not for
		garbage. Worth pinning: if the constraint is ever dropped, the guard
		becomes the only thing standing between a form button and a traceback.
		"""
		request = self._request()
		instance = self._instance_with_drive_file(request, {})

		with self.assertRaises(Exception):
			frappe.db.set_value(
				"BPMN Process Instance",
				instance,
				"workflow_state",
				"not json",
				update_modified=False,
			)
		frappe.db.rollback()

	def test_a_run_with_no_task_data_at_all_does_not_raise(self):
		"""NULL is the only falsy value the JSON-constrained column accepts —
		an instance that errored before its first checkpoint looks like this."""
		request = self._request()
		instance = self._instance_with_drive_file(request, {})
		frappe.db.sql(
			"update `tabBPMN Process Instance` set workflow_state = NULL where name = %s",
			instance,
		)

		self.assertEqual(get_published_document_link(request), {})

	def test_drive_file_of_the_wrong_shape_is_ignored(self):
		request = self._request()
		instance = self._instance_with_drive_file(request, {})
		frappe.db.set_value(
			"BPMN Process Instance",
			instance,
			"workflow_state",
			json.dumps({"data": {"drive_file": "just-a-string"}}),
			update_modified=False,
		)

		self.assertEqual(get_published_document_link(request), {})


class TestBackfillPatch(DocumentRequestFixtures, unittest.TestCase):
	"""The patch turns the fallback into the preferred path for old requests."""

	def test_published_request_gets_linked_to_its_index_entry(self):
		from one_fm.patches.v15_0.link_published_document_requests import _index_entry_for

		request = self._request()
		self._instance_with_drive_file(request, {"id": FILE_ID, "webViewLink": WEB_VIEW_LINK})

		self.assertEqual(_index_entry_for(request), FILE_ID)

	def test_matching_is_by_file_id_not_title(self):
		"""Two requests can publish documents with the same title — a re-run is
		the normal case — so the file id is what identifies the entry."""
		from one_fm.patches.v15_0.link_published_document_requests import _index_entry_for

		first = self._request()
		second = self._request()
		self._instance_with_drive_file(first, {"id": "file-one", "webViewLink": "u1"})
		self._instance_with_drive_file(second, {"id": "file-two", "webViewLink": "u2"})

		self.assertEqual(_index_entry_for(first), "file-one")
		self.assertEqual(_index_entry_for(second), "file-two")

	def test_a_request_with_no_run_is_skipped(self):
		from one_fm.patches.v15_0.link_published_document_requests import _index_entry_for

		self.assertIsNone(_index_entry_for(self._request()))
